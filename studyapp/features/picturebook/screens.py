import os
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
from kivy.properties import ListProperty

from .repository import get_today_record, upsert_record, get_recent_records, get_stats
from ..flashcards.screens import _bind_exclusive_focus

kv_path = os.path.join(os.path.dirname(__file__), 'picturebook.kv')
Builder.load_file(kv_path)


class ChartWidget(Widget):
    """自定义图表组件 - 柱状图(绘本数量) + 折线图(正确率) + 触摸提示"""
    records = ListProperty([])

    def __init__(self, **kw):
        super().__init__(**kw)
        self._bar_positions = []  # [(x, y, w, h, record), ...]
        self._tooltip = None

    def on_records(self, instance, value):
        self.draw_chart()

    def draw_chart(self):
        self.canvas.clear()
        self._bar_positions = []
        if not self.records:
            self._clear_labels()
            return

        app = App.get_running_app()
        w, h = self.size
        x, y = self.pos
        if w < 10 or h < 10:
            return

        n = len(self.records)
        max_books = max((r.book_count for r in self.records), default=1) or 1

        # 图表区域: 左边50px(Y轴), 右边50px(百分比轴), 底部35px(日期), 上下10px
        left = x + 50
        right = x + w - 50
        bottom = y + 35
        top = y + h - 10
        chart_w = right - left
        chart_h = top - bottom

        if chart_w < 20 or chart_h < 20:
            return

        bar_w = chart_w / n * 0.6
        gap = chart_w / n

        with self.canvas:
            # 背景网格线 (4条水平线)
            Color(*app.color_border)
            for i in range(1, 5):
                gy = bottom + chart_h * i / 4
                Line(points=[left, gy, right, gy], width=0.5)

            # 柱状图 - 绘本数量
            Color(*app.color_accent, a=0.7)
            for i, rec in enumerate(self.records):
                bx = left + gap * i + (gap - bar_w) / 2
                bh = (rec.book_count / max_books) * chart_h if max_books else 0
                Rectangle(pos=(bx, bottom), size=(bar_w, bh))
                self._bar_positions.append((bx, bottom, bar_w, bh, rec))

            # 折线图 - 正确率
            Color(*app.color_success)
            points = []
            for i, rec in enumerate(self.records):
                lx = left + gap * i + gap / 2
                ly = bottom + (rec.accuracy / 100) * chart_h
                points.extend([lx, ly])
            if len(points) >= 4:
                Line(points=points, width=2)
            # 折线上的圆点
            Color(*app.color_success)
            for i, rec in enumerate(self.records):
                lx = left + gap * i + gap / 2
                ly = bottom + (rec.accuracy / 100) * chart_h
                Rectangle(pos=(lx - 4, ly - 4), size=(8, 8))

        # 标签
        self._draw_labels(app, x, left, right, bottom, top, gap, max_books, y)

    def _draw_labels(self, app, x, left, right, bottom, top, gap, max_books, y):
        self._clear_labels()

        # X轴日期标签
        for i, rec in enumerate(self.records):
            lx = left + gap * i + gap / 2
            lbl = Label(
                text=rec.date[5:],  # MM-DD
                font_size=14,
                color=app.color_text_sec,
                size_hint=(None, None),
                size=(gap, 20),
                pos=(lx - gap / 2, y + 5),
                halign='center',
            )
            self.add_widget(lbl)

        # 左Y轴 - 绘本数量
        self.add_widget(Label(text=str(max_books), font_size=14, color=app.color_text_sec,
                              size_hint=(None, None), size=(45, 20),
                              pos=(x, top - 10), halign='right'))
        self.add_widget(Label(text='0', font_size=14, color=app.color_text_sec,
                              size_hint=(None, None), size=(45, 20),
                              pos=(x, bottom - 10), halign='right'))

        # 右Y轴 - 百分比
        rx = right + 5
        self.add_widget(Label(text='100%', font_size=14, color=app.color_success,
                              size_hint=(None, None), size=(45, 20),
                              pos=(rx, top - 10)))
        self.add_widget(Label(text='50%', font_size=14, color=app.color_success,
                              size_hint=(None, None), size=(45, 20),
                              pos=(rx, (top + bottom) / 2 - 10)))
        self.add_widget(Label(text='0%', font_size=14, color=app.color_success,
                              size_hint=(None, None), size=(45, 20),
                              pos=(rx, bottom - 10)))

    def _clear_labels(self):
        for child in list(self.children):
            self.remove_widget(child)
        self._tooltip = None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self._show_tooltip(touch.pos)
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        self._show_tooltip(touch.pos)
        return True

    def on_touch_up(self, touch):
        self._hide_tooltip()

    def _show_tooltip(self, pos):
        # 找到触摸位置对应的柱状图
        for bx, by, bw, bh, rec in self._bar_positions:
            if bx <= pos[0] <= bx + bw:
                self._hide_tooltip()
                app = App.get_running_app()
                self._tooltip = Label(
                    text=f'{rec.date[5:]}\n{rec.book_count}本  {int(rec.accuracy)}%',
                    font_size=18,
                    color=app.color_text,
                    size_hint=(None, None),
                    size=(120, 50),
                    pos=(bx + bw / 2 - 60, by + bh + 5),
                    halign='center',
                    valign='bottom',
                )
                with self._tooltip.canvas.before:
                    Color(*app.color_bg_card)
                    Rectangle(pos=self._tooltip.pos, size=self._tooltip.size)
                    Color(*app.color_border)
                    Line(rectangle=(*self._tooltip.pos, *self._tooltip.size), width=1)
                self.add_widget(self._tooltip)
                return
        self._hide_tooltip()

    def _hide_tooltip(self):
        if self._tooltip:
            self.remove_widget(self._tooltip)
            self._tooltip = None


class PictureBookScreen(Screen):
    """绘本打卡页"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._days = 7

    def on_enter(self):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        today = datetime.now().strftime('%Y-%m-%d')
        record = get_today_record()

        if record:
            self.ids.today_status.text = f'{today}  已读 {record.book_count} 本  正确率 {int(record.accuracy)}%'
            self.ids.btn_checkin.text = '修改'
        else:
            self.ids.today_status.text = f'{today}  今日尚未打卡'
            self.ids.btn_checkin.text = '打卡'

        self._update_chart()
        self._update_stats()

    def _update_stats(self):
        periods = [('stats_1w', 7), ('stats_1m', 30), ('stats_3m', 90), ('stats_1y', 365)]
        for wid, days in periods:
            s = get_stats(days)
            self.ids[wid].text = f'{s["total_books"]}本 / 均正确{s["avg_accuracy"]}%'

    def _update_chart(self):
        records = get_recent_records(self._days)
        # 填充空白天
        self.ids.chart.records = records
        self.ids.chart_label.text = f'— 绘本数量  — 正确率' if records else '暂无数据'

    def set_range(self, days):
        self._days = days
        app = App.get_running_app()
        for btn_id, d in [('btn_7d', 7), ('btn_30d', 30)]:
            active = d == days
            self.ids[btn_id].color = (1, 1, 1, 1) if active else app.color_text_sec
            self.ids[btn_id].background_color = app.color_accent if active else app.color_bg_card
        self._update_chart()

    def show_checkin_popup(self):
        app = App.get_running_app()
        record = get_today_record()

        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        count_input = TextInput(
            text=str(record.book_count) if record else '',
            hint_text='阅读绘本数量', font_size=28,
            size_hint_y=None, height=60,
            foreground_color=app.color_text, input_filter='int',
        )
        acc_input = TextInput(
            text=str(int(record.accuracy)) if record else '',
            hint_text='答题正确率 (如 75 或 5/8)', font_size=28,
            size_hint_y=None, height=60,
            foreground_color=app.color_text,
        )
        btns = BoxLayout(size_hint_y=None, height=60, spacing=20)
        confirm = Button(text='保存', font_size=28, background_normal='', background_down='',
                         background_color=app.color_accent, color=(1, 1, 1, 1))
        cancel = Button(text='取消', font_size=28, background_normal='', background_down='',
                        background_color=app.color_text_sec, color=(1, 1, 1, 1))
        btns.add_widget(confirm)
        btns.add_widget(cancel)

        content.add_widget(count_input)
        content.add_widget(acc_input)
        _bind_exclusive_focus([count_input, acc_input])
        content.add_widget(btns)

        popup = Popup(title='绘本打卡', content=content, size_hint=(0.4, 0.35),
                      background='', background_color=app.color_bg_card,
                      title_color=app.color_text, separator_color=app.color_border)

        def _dismiss(p):
            for child in p.content.walk():
                if isinstance(child, TextInput) and child.focus:
                    child.focus = False
            p.dismiss()

        cancel.bind(on_release=lambda b: _dismiss(popup))

        def _parse_accuracy(text):
            text = text.strip()
            if not text:
                return 0
            if '/' in text:
                parts = text.split('/')
                if len(parts) == 2:
                    try:
                        num, den = float(parts[0]), float(parts[1])
                        return round(num / den * 100) if den > 0 else 0
                    except ValueError:
                        return 0
            try:
                return int(text)
            except ValueError:
                return 0

        def do_save(instance):
            c = int(count_input.text.strip()) if count_input.text.strip() else 0
            a = _parse_accuracy(acc_input.text)
            if c > 0:
                upsert_record(c, min(100, max(0, a)))
            _dismiss(popup)
            self.refresh()

        confirm.bind(on_release=do_save)
        popup.open()


def register_screens(screen_manager):
    screen_manager.add_widget(PictureBookScreen(name='picturebook'))
