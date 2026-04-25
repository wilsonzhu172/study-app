import os

# 必须在导入kivy之前设置环境变量
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_KV'] = '1'

# 设置中文字体
_font_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'NotoSansSC-Regular.ttf')
if os.path.exists(_font_path):
    _font_path = os.path.abspath(_font_path)
    from kivy.config import Config
    Config.set('kivy', 'default_font', [_font_path, _font_path, _font_path, _font_path])
    if not os.environ.get('ANDROID_ROOT'):
        Config.set('kivy', 'keyboard_mode', 'systemandmulti')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.clock import Clock

from studyapp.core.database import init_db, backup_db
from studyapp.core.theme import LIGHT, DARK
from studyapp.features.flashcards.screens import register_screens as register_flashcards
from studyapp.features.dictionary.screens import register_screens as register_dictionary
from studyapp.features.picturebook.screens import register_screens as register_picturebook
from studyapp.features.quiz.screens import register_screens as register_quiz

# 窗口大小 (适配21.5寸学习机横屏, Android上使用全屏)
if not os.environ.get('ANDROID_ROOT'):
    Window.size = (1920, 1080)

# 加载根KV布局
kv_path = os.path.join(os.path.dirname(__file__), 'studyapp.kv')
if not Builder.files:
    Builder.load_file(kv_path)


class RootWidget(BoxLayout):
    """根布局 - 顶部导航 + 内容区 + 底部导航"""

    # 当前激活的底部导航标签
    active_tab = StringProperty('flashcards')

    def on_touch_down(self, touch):
        from kivy.uix.textinput import TextInput
        from kivy.uix.vkeyboard import VKeyboard
        from kivy.uix.popup import Popup

        # 点击虚拟键盘时不取消焦点，让键盘正常工作
        for vk in Window.children:
            if isinstance(vk, VKeyboard) and vk.collide_point(*touch.pos):
                return super().on_touch_down(touch)

        # 查找当前聚焦的TextInput (包括Popup内的)
        focused = self._find_focused(self)
        if not focused:
            for child in Window.children:
                if isinstance(child, Popup):
                    focused = self._find_focused(child)
                    if focused:
                        break

        # 点击输入框外部时收起键盘
        if focused and not focused.collide_point(*touch.pos):
            focused.focus = False

        # 延迟一帧清理多余虚拟键盘 (在focus切换和新键盘创建之后)
        Clock.schedule_once(self._dedup_vkeyboards)
        return super().on_touch_down(touch)

    @staticmethod
    def _dedup_vkeyboards(dt):
        from kivy.uix.vkeyboard import VKeyboard
        vks = [c for c in Window.children if isinstance(c, VKeyboard)]
        while len(vks) > 1:
            Window.remove_widget(vks.pop(0))

    def _find_focused(self, widget):
        """递归查找当前聚焦的TextInput"""
        from kivy.uix.textinput import TextInput
        if isinstance(widget, TextInput) and widget.focus:
            return widget
        for child in getattr(widget, 'children', []):
            result = self._find_focused(child)
            if result:
                return result
        return None

    def show_flashcards(self):
        """切换到卡片学习页"""
        self.ids.sm.current = 'deck_list'
        self.active_tab = 'flashcards'

    def show_dictionary(self):
        """切换到英文词典页"""
        self.ids.sm.current = 'dictionary'
        self.active_tab = 'dictionary'

    def show_vocab(self):
        """切换到生词本页"""
        self.ids.sm.current = 'vocab_list'
        self.active_tab = 'vocab'

    def show_picturebook(self):
        """切换到绘本打卡页"""
        self.ids.sm.current = 'picturebook'
        self.active_tab = 'picturebook'

    def show_quiz(self):
        """切换单词测验页"""
        self.ids.sm.current = 'quiz'
        self.active_tab = 'quiz'


class StudyApp(App):
    """学习助手主应用 - 支持亮色/暗黑主题切换"""

    # 主题色彩属性，KV中通过 app.color_xxx 引用
    color_bg = ListProperty(LIGHT['bg'])
    color_bg_card = ListProperty(LIGHT['bg_card'])
    color_bg_nav = ListProperty(LIGHT['bg_nav'])
    color_text = ListProperty(LIGHT['text'])
    color_text_sec = ListProperty(LIGHT['text_sec'])
    color_accent = ListProperty(LIGHT['accent'])
    color_accent_light = ListProperty(LIGHT['accent_light'])
    color_success = ListProperty(LIGHT['success'])
    color_warning = ListProperty(LIGHT['warning'])
    color_danger = ListProperty(LIGHT['danger'])
    color_border = ListProperty(LIGHT['border'])
    color_shadow = ListProperty(LIGHT['shadow'])

    # 主题切换按钮文字
    theme_label = StringProperty('深色模式')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_dark = False

    def build(self):
        self._request_storage_permission()
        init_db()
        root = RootWidget()
        register_flashcards(root.ids.sm)
        register_dictionary(root.ids.sm)
        register_picturebook(root.ids.sm)
        register_quiz(root.ids.sm)
        root.ids.sm.current = 'deck_list'
        return root

    @staticmethod
    def _request_storage_permission():
        """请求存储权限 (Android 11+ 需要 MANAGE_EXTERNAL_STORAGE)"""
        try:
            from jnius import autoclass
            Environment = autoclass('android.os.Environment')
            if hasattr(Environment, 'isExternalStorageManager'):
                if not Environment.isExternalStorageManager():
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    Intent = autoclass('android.content.Intent')
                    Settings = autoclass('android.provider.Settings')
                    Uri = autoclass('android.net.Uri')
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    intent.setData(Uri.parse('package:com.studyapp.studyapp'))
                    PythonActivity.mActivity.startActivity(intent)
                    return
        except (ImportError, Exception):
            pass
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
        except (ImportError, Exception):
            pass

    def toggle_theme(self):
        """切换亮色/暗黑主题，更新所有颜色属性"""
        self._is_dark = not self._is_dark
        theme = DARK if self._is_dark else LIGHT
        self.color_bg = theme['bg']
        self.color_bg_card = theme['bg_card']
        self.color_bg_nav = theme['bg_nav']
        self.color_text = theme['text']
        self.color_text_sec = theme['text_sec']
        self.color_accent = theme['accent']
        self.color_accent_light = theme['accent_light']
        self.color_success = theme['success']
        self.color_warning = theme['warning']
        self.color_danger = theme['danger']
        self.color_border = theme['border']
        self.color_shadow = theme['shadow']
        self.theme_label = '浅色模式' if self._is_dark else '深色模式'

    def quit_app(self):
        """备份数据库并退出应用"""
        backup_db()
        from kivy.core.window import Window
        Window.close()


if __name__ == '__main__':
    StudyApp().run()
