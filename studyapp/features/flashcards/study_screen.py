import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color as ColorInstr

from .repository import get_cards_by_deck, get_deck, add_study_record, get_vocab_deck_id, checkin_deck, get_due_cards, get_new_cards
from .study_engine import get_study_cards, grade_label, process_grade

kv_path = os.path.join(os.path.dirname(__file__), 'flashcards.kv')


class StudyScreen(Screen):
    """学习页 - 翻卡片 + 评分"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._cards = []
        self._index = 0
        self._total = 0
        self._flipped = False
        self._is_daily = False

    def start_study(self, deck_id):
        """开始学习指定牌组"""
        self._deck_id = deck_id
        deck = get_deck(deck_id)
        self.ids.study_title.text = deck.name
        self._is_daily = deck.is_system == 2
        if self._is_daily:
            self._cards = get_new_cards(deck_id) + get_due_cards(deck_id)
        else:
            self._cards = get_study_cards(deck_id, deck.daily_new_limit)
        self._index = 0
        self._total = len(self._cards)
        self._show_card()
        self.manager.current = 'study'

    def _show_card(self):
        """显示当前卡片正面"""
        app = App.get_running_app()
        if self._index >= len(self._cards):
            # 当日生词本: 未掌握的卡片循环
            if self._is_daily:
                remaining = get_due_cards(self._deck_id)
                if remaining:
                    self._cards = remaining
                    self._index = 0
                    card = self._cards[self._index]
                    self._flipped = False
                    self.ids.card_content.text = card.front
                    self.ids.card_hint.text = '点击卡片查看答案 (未掌握，继续循环)'
                    mastered = self._total - len(remaining)
                    self.ids.progress_label.text = f'已掌握 {mastered}/{self._total}'
                    for btn_id in ('btn_again', 'btn_hard', 'btn_good', 'btn_easy'):
                        self.ids[btn_id].disabled = True
                    card_colors = [c for c in self.ids.card_box.canvas.before.children if isinstance(c, ColorInstr)]
                    if card_colors:
                        card_colors[-1].rgba = app.color_bg_card
                    return

            self.ids.card_content.text = '全部学完！'
            self.ids.card_hint.text = ''
            self.ids.progress_label.text = f'已学 {self._total}/{self._total}'
            if self._total > 0:
                checkin_deck(self._deck_id)
            for btn_id in ('btn_again', 'btn_hard', 'btn_good', 'btn_easy'):
                self.ids[btn_id].disabled = True
            return

        card = self._cards[self._index]
        self._flipped = False
        self.ids.card_content.text = card.front
        self.ids.card_hint.text = '点击卡片查看答案'
        self.ids.progress_label.text = f'已学 {self._index}/{self._total}'

        for btn_id in ('btn_again', 'btn_hard', 'btn_good', 'btn_easy'):
            self.ids[btn_id].disabled = True

        # 恢复卡片背景色 (查找最后一个Color指令 = 卡片背景)
        card_colors = [c for c in self.ids.card_box.canvas.before.children if isinstance(c, ColorInstr)]
        if card_colors:
            card_colors[-1].rgba = app.color_bg_card

    def flip_card(self):
        """翻转卡片 (动画)"""
        if self._flipped or self._index >= len(self._cards):
            return
        self._flipped = True

        card = self._cards[self._index]
        card_box = self.ids.card_box
        anim = Animation(size_hint_x=0.01, duration=0.2)
        anim.bind(on_complete=lambda *a: self._swap_and_grow(card))
        anim.start(card_box)

    def _swap_and_grow(self, card):
        """翻转动画后半段: 切换内容后展开"""
        self.ids.card_content.text = card.back
        self.ids.card_hint.text = '为这张卡片评分'
        anim = Animation(size_hint_x=0.7, duration=0.2)
        anim.start(self.ids.card_box)
        for btn_id in ('btn_again', 'btn_hard', 'btn_good', 'btn_easy'):
            self.ids[btn_id].disabled = False

    def grade_card(self, grade):
        """评分并显示颜色反馈, 更新学习进度"""
        app = App.get_running_app()
        if self._index >= len(self._cards):
            return
        card = self._cards[self._index]
        add_study_record(card.id, grade)

        # 当日生词本: grade>=2 掌握(level=5), grade<2 继续循环(level=0)
        if self._is_daily:
            from datetime import datetime, timedelta
            if grade >= 2:
                new_level = 5
                next_review = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                new_level = 0
                next_review = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            from .repository import upsert_card_progress
            upsert_card_progress(card.id, new_level, next_review)
        else:
            # 普通牌组: 标准间隔重复
            progress = process_grade(card.id, grade)

            # 生词本自动清理: 已掌握的词从vocabulary表删除
            if progress and progress['level'] >= 5:
                vocab_deck_id = get_vocab_deck_id()
                if vocab_deck_id and card.deck_id == vocab_deck_id:
                    from ..dictionary.repository import delete_vocab_by_card_id
                    delete_vocab_by_card_id(card.id)

        # 评分颜色反馈 (半透明覆盖在卡片上)
        colors = {
            0: (0.94, 0.27, 0.27, 0.3),  # 红色-重来
            1: (0.96, 0.62, 0.04, 0.3),   # 黄色-困难
            2: (0.06, 0.72, 0.51, 0.3),   # 绿色-良好
            3: (0.31, 0.42, 0.96, 0.3),   # 蓝色-简单
        }
        card_colors = [c for c in self.ids.card_box.canvas.before.children if isinstance(c, ColorInstr)]
        if card_colors:
            card_colors[-1].rgba = colors.get(grade, app.color_bg_card)

        self._index += 1
        Clock.schedule_once(lambda dt: self._show_card(), 0.5)

    def go_back(self):
        """返回牌组列表"""
        self.manager.current = 'deck_list'

    def on_touch_down(self, touch):
        """点击卡片区域触发翻转"""
        if self.ids.card_box.collide_point(*touch.pos):
            self.flip_card()
        return super().on_touch_down(touch)
