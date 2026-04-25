import os
import re
import random
from datetime import datetime, timedelta

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import BooleanProperty
from kivy.metrics import dp

from studyapp.core.database import get_connection
from studyapp.features.flashcards.study_engine import INTERVAL_DAYS
from studyapp.features.flashcards.repository import get_card_progress, upsert_card_progress

kv_path = os.path.join(os.path.dirname(__file__), 'quiz.kv')
Builder.load_file(kv_path)


class QuizScreen(Screen):
    _questions = []
    _current = None
    _wrong = []
    _total = 0
    _correct = 0
    _selected_index = None
    _submitted = False

    def on_enter(self):
        self._load_questions()

    @staticmethod
    def _is_english(text):
        return bool(re.match(r'^[a-zA-Z\s\'-]+$', text.strip()))

    def _load_questions(self):
        conn = get_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        seen = set()
        word_list = []

        # 来源1: 今日词典查词
        for r in conn.execute(
            "SELECT word, translation, card_id FROM vocabulary "
            "WHERE DATE(created_at) = ? AND translation IS NOT NULL AND translation != ''",
            (today,),
        ).fetchall():
            w = r['word'].strip().lower()
            if w not in seen:
                seen.add(w)
                word_list.append({
                    'word': r['word'],
                    'translation': r['translation'].split('\n')[0].strip(),
                    'card_id': r['card_id'],
                })

        # 来源2: 今日卡片学习中学习过的英文单词
        for r in conn.execute(
            "SELECT DISTINCT c.front, c.back, c.id "
            "FROM study_records sr "
            "JOIN cards c ON sr.card_id = c.id "
            "WHERE DATE(sr.studied_at) = DATE('now','localtime')",
        ).fetchall():
            front = r['front'].strip()
            if not self._is_english(front):
                continue
            w = front.lower()
            if w in seen:
                continue
            seen.add(w)
            back_first = r['back'].split('\n')[0].strip()
            word_list.append({
                'word': front,
                'translation': back_first,
                'card_id': r['id'],
            })

        if not word_list:
            self._show_empty('今日暂无单词可测验\n请先学习单词或查词')
            return

        # 收集所有释义用于干扰选项
        all_translations = set()
        for r in conn.execute(
            "SELECT DISTINCT translation FROM vocabulary "
            "WHERE translation IS NOT NULL AND translation != ''"
        ).fetchall():
            t = r['translation'].split('\n')[0].strip()
            if t:
                all_translations.add(t)
        for item in word_list:
            if item['translation']:
                all_translations.add(item['translation'])
        all_translations = list(all_translations)

        self._questions = []
        self._wrong = []
        self._correct = 0
        self._submitted = False

        for item in word_list:
            if not item['translation']:
                continue
            choices = self._generate_choices(item['translation'], all_translations)
            self._questions.append({
                'word': item['word'],
                'translation': item['translation'],
                'card_id': item['card_id'],
                'choices': choices,
            })

        if not self._questions:
            self._show_empty('今日暂无单词可测验\n请先学习单词或查词')
            return

        self._total = len(self._questions)
        self._show_quiz()
        self._next()

    def _generate_choices(self, correct, all_translations):
        wrong = [t for t in set(all_translations) if t != correct]
        random.shuffle(wrong)
        choices = [correct] + wrong[:4]
        # 不够4个干扰项时，用已有选项补充（避免重复正确答案）
        while len(choices) < 5 and wrong:
            extra = random.choice(wrong)
            if extra not in choices:
                choices.append(extra)
        while len(choices) < 5:
            choices.append(correct + ' (同)')
        random.shuffle(choices)
        return choices

    def _show_quiz(self):
        self.ids.quiz_content.size_hint_y = 1
        self.ids.empty_message.height = 0
        self.ids.empty_message.text = ''

    def _show_empty(self, message):
        self.ids.quiz_content.size_hint_y = None
        self.ids.quiz_content.height = 0
        self.ids.empty_message.height = 400
        self.ids.empty_message.text = message

    def _next(self):
        if not self._questions:
            self._questions = self._wrong[:]
            self._wrong = []

        if not self._questions:
            self._show_complete()
            return

        self._current = self._questions.pop(0)
        self._submitted = False
        self._selected_index = None

        self.ids.question_word.text = self._current['word']
        self._update_progress()
        self._render_choices()
        self.ids.feedback_label.text = ''
        self.ids.feedback_label.color = [0, 0, 0, 0]
        self.ids.confirm_btn.disabled = True
        self.ids.confirm_btn.opacity = 1
        self.ids.next_btn.disabled = True
        self.ids.next_btn.opacity = 0
        self.ids.confirm_btn.parent.width = 200

    def _render_choices(self):
        grid = self.ids.choices_grid
        grid.clear_widgets()
        app = self._get_app()
        for i, choice in enumerate(self._current['choices']):
            btn = Button(
                text=f'  ○  {choice}',
                font_size=26,
                size_hint_y=None,
                height=48,
                halign='left',
                valign='middle',
                text_size=[None, None],
                background_normal='',
                background_down='',
                background_color=app.color_bg_card if hasattr(app, 'color_bg_card') else (1, 1, 1, 1),
                color=app.color_text if hasattr(app, 'color_text') else (0, 0, 0, 1),
            )
            btn._choice_idx = i
            btn.bind(size=btn.setter('text_size'))
            btn.bind(on_press=lambda b: self._on_select(b._choice_idx))
            grid.add_widget(btn)

    def _on_select(self, index):
        self._selected_index = index
        self.ids.confirm_btn.disabled = False
        # 更新选中状态的圆圈样式
        for btn in self.ids.choices_grid.children:
            i = btn._choice_idx
            if i == index:
                btn.text = f'  ●  {self._current["choices"][i]}'
            else:
                btn.text = f'  ○  {self._current["choices"][i]}'

    def confirm_answer(self):
        if self._submitted or self._selected_index is None:
            return
        self._submitted = True

        correct_idx = self._current['choices'].index(self._current['translation'])
        chosen = self._current['choices'][self._selected_index]
        is_correct = chosen == self._current['translation']

        feedback = self.ids.feedback_label
        grid = self.ids.choices_grid

        if is_correct:
            self._correct += 1
            feedback.text = '回答正确!'
            feedback.color = self.app_color('success')
        else:
            self._wrong.append(self._current)
            feedback.text = f'回答错误，正确答案: {self._current["translation"]}'
            feedback.color = self.app_color('danger')
            if self._current['card_id']:
                self._decrease_mastery(self._current['card_id'])

        # 高亮正确/错误选项
        for btn in grid.children:
            i = btn._choice_idx
            if i == correct_idx:
                btn.background_color = (0.2, 0.7, 0.2, 1)
                btn.color = (1, 1, 1, 1)
                btn.text = f'  ●  {self._current["choices"][i]}'
            elif i == self._selected_index and not is_correct:
                btn.background_color = (0.8, 0.2, 0.2, 1)
                btn.color = (1, 1, 1, 1)
                btn.text = f'  ●  {self._current["choices"][i]}'
            btn.disabled = True

        self._update_progress()
        # 隐藏确定，显示下一题
        self.ids.confirm_btn.opacity = 0
        self.ids.confirm_btn.disabled = True
        self.ids.next_btn.opacity = 1
        self.ids.next_btn.disabled = False
        self.ids.confirm_btn.parent.width = 200

    def next_question(self):
        self._next()

    def _update_progress(self):
        answered = self._correct + len(self._wrong)
        remaining = len(self._questions) + len(self._wrong)
        self.ids.progress_label.text = f'剩余 {remaining} 题'
        self.ids.stats_label.text = f'正确 {self._correct}  |  答错 {len(self._wrong)}  |  共 {self._total} 题'

    def _show_complete(self):
        self._show_empty(
            f'测验完成!\n\n'
            f'正确: {self._correct}\n'
            f'答错: {len(self._wrong)}\n'
            f'正确率: {self._correct * 100 // max(self._total, 1)}%'
        )

    def _decrease_mastery(self, card_id):
        progress = get_card_progress(card_id)
        level = progress['level'] if progress else 0
        new_level = max(0, level - 1)
        interval = INTERVAL_DAYS.get(new_level, 0)
        next_review = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d %H:%M:%S')
        upsert_card_progress(card_id, new_level, next_review)

    def app_color(self, name):
        app = self._get_app()
        return getattr(app, f'color_{name}', (1, 1, 1, 1))

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()


def register_screens(screen_manager):
    screen_manager.add_widget(QuizScreen(name='quiz'))
