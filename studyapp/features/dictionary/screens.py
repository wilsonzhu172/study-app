import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.text import LabelBase

from .lookup import lookup_word
from .repository import save_or_update_vocab, get_all_vocab, delete_vocab
from .audio import play_audio
from .models import WordEntry
from ..flashcards.repository import create_card, get_vocab_deck_id

# 注册支持IPA音标的字体
_ipa_font = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'fonts', 'NotoSans-Regular.ttf')
_ipa_font = os.path.normpath(_ipa_font)
if os.path.exists(_ipa_font):
    LabelBase.register(name='IPAFont', fn_regular=_ipa_font)

# 加载词典模块的KV样式
kv_path = os.path.join(os.path.dirname(__file__), 'dictionary.kv')
Builder.load_file(kv_path)


class VocabRow(BoxLayout):
    """生词行组件"""
    pass


class DictionaryScreen(Screen):
    """英文词典页 - 搜索单词并查看详情"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._current_entry = None

    def do_search(self, word=None):
        """执行单词搜索"""
        if word is None:
            word = self.ids.search_input.text.strip()
            self.ids.search_input.focus = False
        if not word:
            return
        self.ids.search_input.text = word
        self.ids.result_word.text = '查询中...'
        self.ids.result_phonetic.text = ''
        self.ids.result_translation.text = ''
        self.ids.result_definition.text = ''
        self.ids.result_example.text = ''
        self.ids.status_label.text = ''

        Clock.schedule_once(lambda dt: self._perform_lookup(word))

    def _perform_lookup(self, word):
        """执行实际的词典查询"""
        entry = lookup_word(word)
        self._current_entry = entry

        if not entry.translation and not entry.definition:
            self.ids.result_word.text = f'未找到: {word}'
            return

        self.ids.result_word.text = entry.word
        self.ids.result_phonetic.text = entry.phonetic
        self.ids.result_translation.text = entry.translation or ''
        self.ids.result_definition.text = entry.definition or ''
        if entry.example:
            self.ids.result_example.text = f'例句: {entry.example}'
        else:
            self.ids.result_example.text = ''

        # 添加到搜索历史
        self._add_history(entry.word)
        # 自动保存到生词本并创建卡片
        self._save_to_vocab(entry)

    def _save_to_vocab(self, entry: WordEntry):
        """保存到生词本并自动创建卡片，同时同步到当日生词本"""
        deck_id = get_vocab_deck_id()
        card_id = None
        back_parts = [entry.translation or entry.definition]
        if entry.example:
            back_parts.append(f'例: {entry.example}')
        back = '\n'.join(back_parts)

        if deck_id:
            from ..flashcards.repository import get_card_by_source_ref, update_card
            existing = get_card_by_source_ref(deck_id, entry.word)
            if existing:
                update_card(existing.id, None, back)
                card_id = existing.id
            else:
                card_id = create_card(deck_id, entry.word, back, source='dictionary', source_ref=entry.word)
        save_or_update_vocab(entry, card_id)

        # 同步到当日生词本
        from ..flashcards.repository import get_daily_deck_id, add_to_daily_deck
        daily_id = get_daily_deck_id()
        if daily_id:
            add_to_daily_deck(daily_id, entry.word, back)

        self.ids.status_label.text = '已加入生词本'

    def _add_history(self, word):
        """添加到搜索历史"""
        app = App.get_running_app()
        history = self.ids.history_list
        # 去重: 先移除已有的同一单词
        for child in list(history.children):
            if hasattr(child, '_history_word') and child._history_word == word:
                history.remove_widget(child)
        btn = Button(text=word, font_size=24, size_hint_y=None, height=50,
                     color=app.color_text, background_normal='', background_down='',
                     background_color=app.color_accent_light,
                     halign='left', valign='middle', padding=(10, 0))
        btn._history_word = word
        btn.bind(on_release=lambda b: self.do_search(word))
        history.add_widget(btn)

    def play_pronunciation(self):
        """播放单词发音"""
        if not self._current_entry:
            return
        if not self._current_entry.audio_url:
            self.ids.status_label.text = '暂无音频'
            return
        self.ids.status_label.text = '播放中...'
        play_audio(self._current_entry.audio_url, on_stop=self._on_audio_stop)

    def _on_audio_stop(self):
        if self.ids.status_label.text == '播放中...':
            self.ids.status_label.text = ''

    def on_enter(self):
        pass


class VocabListScreen(Screen):
    """生词本列表页"""

    def on_enter(self):
        self.refresh()

    def refresh(self):
        """刷新生词列表"""
        app = App.get_running_app()
        container = self.ids.vocab_grid
        container.clear_widgets()

        # 表头
        header = BoxLayout(size_hint_y=None, height=60, spacing=10)
        for text, width in [('单词', 0.2), ('音标', 0.15), ('释义', 0.45), ('次数', 0.1), ('', 0.1)]:
            lbl = Label(text=text, font_size=26, bold=True, size_hint_x=width,
                        color=app.color_text)
            header.add_widget(lbl)
        container.add_widget(header)

        # 数据行
        from studyapp.core.database import get_connection
        rows = get_connection().execute(
            "SELECT word, phonetic, translation, lookup_count FROM vocabulary ORDER BY created_at DESC"
        ).fetchall()

        for r in rows:
            row = BoxLayout(size_hint_y=None, height=50, spacing=10)
            row.add_widget(Label(text=r['word'], font_size=24, size_hint_x=0.2,
                                 color=app.color_text))
            phonetic_lbl = Label(text=r['phonetic'], font_size=22, size_hint_x=0.15,
                                 color=app.color_text_sec)
            phonetic_lbl.font_name = 'IPAFont'
            row.add_widget(phonetic_lbl)
            row.add_widget(Label(text=r['translation'][:40], font_size=22, size_hint_x=0.45,
                                 color=app.color_text_sec, halign='left', valign='middle',
                                 text_size=(None, None)))
            row.add_widget(Label(text=str(r['lookup_count']), font_size=22, size_hint_x=0.1,
                                 color=app.color_text_sec))

            btn = Button(text='删除', font_size=20, size_hint_x=0.1,
                         background_normal='', background_down='',
                         background_color=app.color_danger, color=(1, 1, 1, 1))
            word = r['word']
            btn.bind(on_release=lambda b, w=word: self._delete_vocab(w))
            row.add_widget(btn)
            container.add_widget(row)

    def _delete_vocab(self, word):
        """从生词本中删除指定单词"""
        delete_vocab(word)
        self.refresh()

    def _lookup_again(self, word):
        """跳转到词典重新查词"""
        sm = self.manager
        dict_screen = sm.get_screen('dictionary')
        sm.current = 'dictionary'
        sm.parent.active_tab = 'dictionary'
        Clock.schedule_once(lambda dt: dict_screen.do_search(word), 0.3)


def register_screens(screen_manager):
    """注册词典相关屏幕"""
    screen_manager.add_widget(DictionaryScreen(name='dictionary'))
    screen_manager.add_widget(VocabListScreen(name='vocab_list'))
