import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView

from .repository import (
    get_decks, get_deck, create_deck, update_deck, delete_deck,
    get_cards_by_deck, get_card, create_card, update_card, delete_card,
    get_card_count, get_learned_count, get_preset_decks, import_preset_deck,
    update_deck_daily_limit, is_deck_checked_in,
)
from .study_screen import StudyScreen

# 加载卡片学习模块的KV样式
kv_path = os.path.join(os.path.dirname(__file__), 'flashcards.kv')
Builder.load_file(kv_path)


def _dismiss_and_unfocus(popup):
    """关闭弹窗前取消所有TextInput焦点，确保虚拟键盘收起"""
    for child in popup.content.walk():
        if isinstance(child, TextInput) and child.focus:
            child.focus = False
    popup.dismiss()


def _bind_exclusive_focus(inputs):
    """让一组TextInput互斥聚焦：只有一个获得焦点时，其余全部失去焦点"""
    def _on_focus(instance, value):
        if value:
            for inp in inputs:
                if inp is not instance and inp.focus:
                    inp.focus = False
    for inp in inputs:
        inp.bind(focus=_on_focus)


class DeckTile(BoxLayout):
    """牌组卡片组件 - 在KV中定义样式"""
    pass


class DeckListScreen(Screen):
    """牌组列表页 - 显示所有牌组"""

    def on_enter(self):
        self.refresh()

    def refresh(self):
        """刷新牌组列表"""
        container = self.ids.deck_grid
        container.clear_widgets()
        for deck in get_decks():
            total = get_card_count(deck.id)
            learned = get_learned_count(deck.id)
            pct = int(learned / total * 100) if total else 0
            tile = DeckTile()
            tile.ids.deck_name.text = deck.name
            tile.ids.deck_desc.text = deck.description or f'{total}张卡片'
            tile.ids.deck_progress.text = f'掌握 {pct}% ({learned}/{total})'
            tile.ids.deck_limit.text = '' if deck.is_system == 2 else f'每日新卡: {deck.daily_new_limit}'
            tile.ids.deck_checkin.text = '已打卡' if is_deck_checked_in(deck.id) else ''
            tile.ids.color_bar.background_color = self._hex_to_rgba(deck.color)
            tile.deck_id = deck.id
            tile.is_system = deck.is_system
            tile.daily_new_limit = deck.daily_new_limit

            tile.ids.btn_study.bind(on_release=lambda b, d=deck.id: self.study_deck(d))
            tile.ids.btn_edit.bind(on_release=lambda b, d=deck.id: self.edit_cards(d))
            tile.ids.btn_delete.bind(on_release=lambda b, d=deck.id, sys=deck.is_system:
                                      self.confirm_delete(d) if not sys else self.batch_delete_cards(d))
            tile.ids.deck_limit.bind(on_release=lambda b, d=deck.id: self.show_deck_settings(d))

            container.add_widget(tile)

    @staticmethod
    def _hex_to_rgba(hex_color):
        """将十六进制颜色转为RGBA元组"""
        try:
            h = hex_color.lstrip('#')
            return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (1,)
        except (ValueError, IndexError):
            return (0.3, 0.6, 1.0, 1)

    def show_add_deck(self):
        """弹出新建牌组对话框"""
        app = App.get_running_app()
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        name_input = TextInput(hint_text='牌组名称', font_size=28, size_hint_y=None, height=60,
                               foreground_color=app.color_text)
        desc_input = TextInput(hint_text='描述(可选)', font_size=28, size_hint_y=None, height=60,
                               foreground_color=app.color_text)
        color_input = TextInput(hint_text='颜色(如 #2196F3)', font_size=28, size_hint_y=None, height=60,
                                foreground_color=app.color_text)
        limit_input = TextInput(hint_text='每日新卡数量(默认20)', font_size=28, size_hint_y=None, height=60,
                                foreground_color=app.color_text, input_filter='int')

        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        confirm = Button(text='确定', font_size=28, background_normal='', background_down='',
                         background_color=app.color_accent, color=(1, 1, 1, 1))
        cancel = Button(text='取消', font_size=28, background_normal='', background_down='',
                        background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(confirm)
        btns.add_widget(cancel)

        content.add_widget(name_input)
        content.add_widget(desc_input)
        content.add_widget(color_input)
        content.add_widget(limit_input)
        _bind_exclusive_focus([name_input, desc_input, color_input, limit_input])
        content.add_widget(btns)

        popup = Popup(title='新建牌组', content=content, size_hint=(0.5, 0.5),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        cancel.bind(on_release=lambda b: _dismiss_and_unfocus(popup))

        def do_create(instance):
            name = name_input.text.strip()
            if name:
                limit = int(limit_input.text.strip()) if limit_input.text.strip() else 20
                create_deck(name, desc_input.text.strip(), color_input.text.strip() or '#4CAF50', limit)
                _dismiss_and_unfocus(popup)
                self.refresh()

        confirm.bind(on_release=do_create)
        popup.open()

    def show_deck_settings(self, deck_id):
        """牌组设置弹窗 - 修改每日新卡数量"""
        app = App.get_running_app()
        deck = get_deck(deck_id)
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        content.add_widget(Label(text=f'牌组: {deck.name}', font_size=28, color=app.color_text,
                                 size_hint_y=None, height=50))
        limit_input = TextInput(text=str(deck.daily_new_limit), hint_text='每日新卡数量',
                                font_size=28, size_hint_y=None, height=60,
                                foreground_color=app.color_text, input_filter='int')

        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        confirm = Button(text='保存', font_size=28, background_normal='', background_down='',
                         background_color=app.color_accent, color=(1, 1, 1, 1))
        cancel = Button(text='取消', font_size=28, background_normal='', background_down='',
                        background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(confirm)
        btns.add_widget(cancel)

        content.add_widget(limit_input)
        content.add_widget(btns)

        popup = Popup(title='牌组设置', content=content, size_hint=(0.4, 0.35),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        cancel.bind(on_release=lambda b: _dismiss_and_unfocus(popup))

        def do_save(instance):
            val = int(limit_input.text.strip()) if limit_input.text.strip() else 20
            update_deck_daily_limit(deck_id, max(1, val))
            _dismiss_and_unfocus(popup)
            self.refresh()

        confirm.bind(on_release=do_save)
        popup.open()

    def study_deck(self, deck_id):
        """开始学习指定牌组"""
        sm = self.manager
        study_screen = sm.get_screen('study')
        study_screen.start_study(deck_id)
        sm.current = 'study'

    def edit_cards(self, deck_id):
        """进入卡片编辑页"""
        sm = self.manager
        editor = sm.get_screen('card_editor')
        editor.load_deck(deck_id)
        sm.current = 'card_editor'

    def confirm_delete(self, deck_id):
        """确认删除牌组弹窗"""
        app = App.get_running_app()
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        content.add_widget(Label(text='确定删除这个牌组？', font_size=28, color=app.color_text))
        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        yes = Button(text='删除', font_size=28, background_normal='', background_down='',
                     background_color=app.color_danger, color=(1, 1, 1, 1))
        no = Button(text='取消', font_size=28, background_normal='', background_down='',
                    background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(yes)
        btns.add_widget(no)
        content.add_widget(btns)

        popup = Popup(title='确认', content=content, size_hint=(0.4, 0.3),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        no.bind(on_release=popup.dismiss)
        yes.bind(on_release=lambda _: (delete_deck(deck_id), popup.dismiss(), self.refresh()))
        popup.open()

    def batch_delete_cards(self, deck_id):
        """批量删除卡片弹窗 (用于系统牌组)"""
        app = App.get_running_app()
        cards = get_cards_by_deck(deck_id)
        if not cards:
            return
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll = ScrollView(size_hint_y=0.85)
        grid = GridLayout(cols=1, spacing=8, size_hint_y=None, height=0)
        checkboxes = []
        for card in cards:
            row = BoxLayout(size_hint_y=None, height=50, spacing=10)
            cb = CheckBox(active=False, size_hint_x=0.1)
            checkboxes.append((cb, card.id))
            lbl = Label(text=card.front if len(card.front) <= 25 else card.front[:25] + '...',
                        font_size=24, size_hint_x=0.9, color=app.color_text,
                        halign='left', valign='middle')
            row.add_widget(cb)
            row.add_widget(lbl)
            grid.add_widget(row)
            grid.height += 58
        scroll.add_widget(grid)
        content.add_widget(scroll)

        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        del_btn = Button(text='删除选中', font_size=28,
                         background_normal='', background_down='',
                         background_color=app.color_danger, color=(1, 1, 1, 1))
        cancel_btn = Button(text='取消', font_size=28,
                            background_normal='', background_down='',
                            background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(del_btn)
        btns.add_widget(cancel_btn)
        content.add_widget(btns)

        popup = Popup(title='选择要删除的卡片', content=content, size_hint=(0.6, 0.6),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        cancel_btn.bind(on_release=popup.dismiss)

        def do_delete(instance):
            for cb, cid in checkboxes:
                if cb.active:
                    delete_card(cid)
            popup.dismiss()
            self.refresh()

        del_btn.bind(on_release=do_delete)
        popup.open()

    def show_import_deck(self):
        """导入预设牌组弹窗"""
        app = App.get_running_app()
        presets = get_preset_decks()
        if not presets:
            return

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll = ScrollView(size_hint_y=0.9)
        grid = GridLayout(cols=1, spacing=12, size_hint_y=None, height=0)

        for p in presets:
            row = BoxLayout(size_hint_y=None, height=90, spacing=15, padding=[10, 5])

            # 色块标识 (用Label+背景色代替canvas)
            color_rgba = self._hex_to_rgba(p['color'])
            color_lbl = Label(text='██', font_size=28, size_hint_x=None, width=30,
                              color=color_rgba)

            # 信息区
            name_lbl = Label(text=p['name'], font_size=28, color=app.color_text,
                             size_hint_x=0.55, bold=True)
            desc_lbl = Label(text=f"{p['description']}  ({p['card_count']}张)",
                             font_size=22, color=app.color_text_sec,
                             size_hint_x=0.25)

            row.add_widget(color_lbl)
            row.add_widget(name_lbl)
            row.add_widget(desc_lbl)

            if p['imported']:
                lbl = Label(text='已导入', font_size=24, size_hint_x=None, width=100,
                            color=app.color_text_sec)
                row.add_widget(lbl)
            else:
                btn = Button(text='导入', font_size=26, size_hint_x=None, width=100,
                             background_normal='', background_down='',
                             background_color=app.color_accent, color=(1, 1, 1, 1))
                pid = p['id']

                def do_import(instance, preset_id=pid):
                    import_preset_deck(preset_id)
                    popup.dismiss()
                    self.refresh()

                btn.bind(on_release=do_import)
                row.add_widget(btn)

            grid.add_widget(row)
            grid.height += 102

        scroll.add_widget(grid)
        content.add_widget(scroll)

        close_btn = Button(text='关闭', font_size=26, size_hint_y=None, height=55,
                           background_normal='', background_down='',
                           background_color=app.color_text_sec, color=(1, 1, 1, 1))
        content.add_widget(close_btn)

        popup = Popup(title='导入预设牌组', content=content, size_hint=(0.7, 0.6),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        close_btn.bind(on_release=popup.dismiss)
        popup.open()


class CardEditorScreen(Screen):
    """卡片编辑页 - 管理牌组内的卡片"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._deck_id = None

    def load_deck(self, deck_id):
        self._deck_id = deck_id
        self.refresh()

    def on_enter(self):
        if self._deck_id:
            self.refresh()

    def refresh(self):
        """刷新卡片列表"""
        app = App.get_running_app()
        container = self.ids.card_list
        container.clear_widgets()

        deck = get_deck(self._deck_id)
        self.ids.editor_title.text = f'编辑: {deck.name}'

        for card in get_cards_by_deck(self._deck_id):
            row = BoxLayout(size_hint_y=None, height=60, spacing=10)
            _front = card.front if len(card.front) <= 20 else card.front[:20] + '...'
            _back = card.back if len(card.back) <= 30 else card.back[:30] + '...'
            front_lbl = Label(text=_front, font_size=24, size_hint_x=0.35, color=app.color_text,
                              halign='left', valign='middle')
            back_lbl = Label(text=_back, font_size=24, size_hint_x=0.35, color=app.color_text_sec,
                             halign='left', valign='middle')

            cid = card.id
            edit_btn = Button(text='编辑', font_size=22, size_hint_x=0.15,
                              background_normal='', background_down='',
                              background_color=app.color_warning, color=(1, 1, 1, 1))
            del_btn = Button(text='删除', font_size=22, size_hint_x=0.15,
                             background_normal='', background_down='',
                             background_color=app.color_danger, color=(1, 1, 1, 1))
            edit_btn.bind(on_release=lambda b, c=cid: self._edit_card(c))
            del_btn.bind(on_release=lambda b, c=cid: self._delete_card(c))

            row.add_widget(front_lbl)
            row.add_widget(back_lbl)
            row.add_widget(edit_btn)
            row.add_widget(del_btn)
            container.add_widget(row)

    def show_add_card(self):
        """添加卡片弹窗"""
        if not self._deck_id:
            return
        app = App.get_running_app()
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        front_input = TextInput(hint_text='正面 (问题)', font_size=28, size_hint_y=None, height=80,
                                foreground_color=app.color_text)
        back_input = TextInput(hint_text='背面 (答案)', font_size=28, size_hint_y=None, height=80,
                               foreground_color=app.color_text)
        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        confirm = Button(text='确定', font_size=28, background_normal='', background_down='',
                         background_color=app.color_accent, color=(1, 1, 1, 1))
        cancel = Button(text='取消', font_size=28, background_normal='', background_down='',
                        background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(confirm)
        btns.add_widget(cancel)
        content.add_widget(front_input)
        content.add_widget(back_input)
        _bind_exclusive_focus([front_input, back_input])
        content.add_widget(btns)

        popup = Popup(title='添加卡片', content=content, size_hint=(0.5, 0.4),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        cancel.bind(on_release=lambda b: _dismiss_and_unfocus(popup))

        def do_add(instance):
            f, b = front_input.text.strip(), back_input.text.strip()
            if f and b:
                create_card(self._deck_id, f, b)
                _dismiss_and_unfocus(popup)
                self.refresh()

        confirm.bind(on_release=do_add)
        popup.open()

    def _edit_card(self, card_id):
        """编辑卡片弹窗"""
        card = get_card(card_id)
        if not card:
            return
        app = App.get_running_app()
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        front_input = TextInput(text=card.front, font_size=28, size_hint_y=None, height=80,
                                foreground_color=app.color_text)
        back_input = TextInput(text=card.back, font_size=28, size_hint_y=None, height=80,
                               foreground_color=app.color_text)
        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        confirm = Button(text='保存', font_size=28, background_normal='', background_down='',
                         background_color=app.color_accent, color=(1, 1, 1, 1))
        cancel = Button(text='取消', font_size=28, background_normal='', background_down='',
                        background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(confirm)
        btns.add_widget(cancel)
        content.add_widget(front_input)
        content.add_widget(back_input)
        _bind_exclusive_focus([front_input, back_input])
        content.add_widget(btns)

        popup = Popup(title='编辑卡片', content=content, size_hint=(0.5, 0.4),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)
        cancel.bind(on_release=lambda b: _dismiss_and_unfocus(popup))

        def do_save(instance):
            update_card(card_id, front_input.text.strip(), back_input.text.strip())
            _dismiss_and_unfocus(popup)
            self.refresh()

        confirm.bind(on_release=do_save)
        popup.open()

    def _delete_card(self, card_id):
        """删除单张卡片"""
        delete_card(card_id)
        self.refresh()

    def go_back(self):
        """返回牌组列表"""
        self.manager.current = 'deck_list'


def register_screens(screen_manager):
    """注册所有卡片学习相关屏幕"""
    screen_manager.add_widget(DeckListScreen(name='deck_list'))
    screen_manager.add_widget(CardEditorScreen(name='card_editor'))
    screen_manager.add_widget(StudyScreen(name='study'))
