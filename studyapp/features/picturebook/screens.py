from datetime import datetime
import tkinter as tk

from .repository import get_today_record, upsert_record, get_recent_records, get_stats


class ChartCanvas(tk.Canvas):
    """柱状图(绘本数量) + 折线图(正确率)"""

    def __init__(self, parent, app, **kw):
        super().__init__(parent, **kw)
        self.app = app
        self._records = []
        self.bind('<Configure>', lambda e: self._draw())

    def set_records(self, records):
        self._records = records
        self._draw()

    def _draw(self):
        self.delete('all')
        t = self.app.theme
        a = self.app
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or h < 50 or not self._records:
            return

        n = len(self._records)
        max_books = max((r.book_count for r in self._records), default=1) or 1

        left, right = a.sx(50), w - a.sx(50)
        bottom, top = h - a.sy(30), a.sy(15)
        chart_w = right - left
        chart_h = bottom - top

        if chart_w < 20 or chart_h < 20:
            return

        bar_w = chart_w / n * 0.6
        gap = chart_w / n

        # 网格线
        for i in range(1, 5):
            gy = top + chart_h * i / 4
            self.create_line(left, gy, right, gy, fill=t['border'], width=1)

        # 柱状图
        for i, rec in enumerate(self._records):
            bx = left + gap * i + (gap - bar_w) / 2
            bh = (rec.book_count / max_books) * chart_h if max_books else 0
            self.create_rectangle(bx, bottom - bh, bx + bar_w, bottom,
                                  fill=t['accent'], outline='', stipple='gray50')

        # 折线图
        points = []
        for i, rec in enumerate(self._records):
            lx = left + gap * i + gap / 2
            ly = bottom - (rec.accuracy / 100) * chart_h
            points.extend([lx, ly])
        if len(points) >= 4:
            self.create_line(*points, fill=t['success'], width=2, smooth=True)

        # 折线圆点
        for i, rec in enumerate(self._records):
            lx = left + gap * i + gap / 2
            ly = bottom - (rec.accuracy / 100) * chart_h
            r = 4
            self.create_oval(lx - r, ly - r, lx + r, ly + r, fill=t['success'], outline='')

        # X轴日期
        for i, rec in enumerate(self._records):
            lx = left + gap * i + gap / 2
            self.create_text(lx, bottom + a.sy(15), text=rec.date[5:], fill=t['text_sec'],
                             font=('Microsoft YaHei', a.s(9)))

        # Y轴标签
        self.create_text(left - a.sx(5), top, text=str(max_books), fill=t['text_sec'],
                         font=('Microsoft YaHei', a.s(9)), anchor='e')
        self.create_text(left - a.sx(5), bottom, text='0', fill=t['text_sec'],
                         font=('Microsoft YaHei', a.s(9)), anchor='e')
        self.create_text(right + a.sx(5), top, text='100%', fill=t['success'],
                         font=('Microsoft YaHei', a.s(9)), anchor='w')
        self.create_text(right + a.sx(5), (top + bottom) / 2, text='50%', fill=t['success'],
                         font=('Microsoft YaHei', a.s(9)), anchor='w')
        self.create_text(right + a.sx(5), bottom, text='0%', fill=t['success'],
                         font=('Microsoft YaHei', a.s(9)), anchor='w')


class PictureBookFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._days = 7
        self._build_ui()

    def _build_ui(self):
        t = self.app.theme
        a = self.app

        # 标题
        tk.Label(self, text='绘本打卡', font=('Microsoft YaHei', a.s(22), 'bold'),
                 bg=t['bg'], fg=t['text']).pack(anchor='w', padx=a.sx(20), pady=(a.sy(15), a.sy(10)))

        # 今日打卡卡片
        today_frame = tk.Frame(self, bg=t['bg_card'], highlightbackground=t['border'],
                               highlightthickness=1, padx=a.sx(20), pady=a.sy(12))
        today_frame.pack(fill='x', padx=a.sx(20), pady=(0, a.sy(10)))

        self._today_label = tk.Label(today_frame, text='今日尚未打卡',
                                     font=('Microsoft YaHei', a.s(15)),
                                     bg=t['bg_card'], fg=t['text'], anchor='w')
        self._today_label.pack(side='left', fill='x', expand=True)

        self._checkin_btn = tk.Button(today_frame, text='打卡',
                                      font=('Microsoft YaHei', a.s(13)),
                                      bg=t['accent'], fg='white', relief='flat',
                                      command=self._show_checkin_popup)
        self._checkin_btn.pack(side='right')

        # 图表区域
        chart_outer = tk.Frame(self, bg=t['bg_card'], highlightbackground=t['border'],
                               highlightthickness=1, padx=a.sx(15), pady=a.sy(10))
        chart_outer.pack(fill='both', expand=True, padx=a.sx(20), pady=(0, a.sy(10)))

        btn_row = tk.Frame(chart_outer, bg=t['bg_card'])
        btn_row.pack(fill='x', pady=(0, a.sy(5)))

        self._btn_7d = tk.Button(btn_row, text='7天', font=('Microsoft YaHei', a.s(11)),
                                 bg=t['accent'], fg='white', relief='flat', width=6,
                                 command=lambda: self._set_range(7))
        self._btn_7d.pack(side='left', padx=(0, a.sx(5)))

        self._btn_30d = tk.Button(btn_row, text='30天', font=('Microsoft YaHei', a.s(11)),
                                  bg=t['bg_card'], fg=t['text_sec'], relief='flat', width=6,
                                  command=lambda: self._set_range(30))
        self._btn_30d.pack(side='left')

        self._chart_label = tk.Label(btn_row, text='', bg=t['bg_card'], fg=t['text_sec'],
                                     font=('Microsoft YaHei', a.s(10)))
        self._chart_label.pack(side='left', padx=a.sx(20))

        self._chart = ChartCanvas(chart_outer, self.app, bg=t['bg_card'], highlightthickness=0)
        self._chart.pack(fill='both', expand=True)

        # 统计摘要 - 手机上2x2, 大屏上4列
        stats_frame = tk.Frame(self, bg=t['bg'])
        stats_frame.pack(fill='x', padx=a.sx(20), pady=(0, a.sy(10)))

        cols = 2 if a.screen_type == 'phone' else 4
        self._stat_labels = {}
        periods = [('1w', '近1周'), ('1m', '近1月'), ('3m', '近3月'), ('1y', '近1年')]
        for idx, (period, label) in enumerate(periods):
            card = tk.Frame(stats_frame, bg=t['bg_card'], highlightbackground=t['border'],
                           highlightthickness=1, padx=a.sx(10), pady=a.sy(8))
            r, c = divmod(idx, cols)
            card.grid(row=r, column=c, sticky='nsew', padx=a.sx(5), pady=a.sy(3))
            stats_frame.grid_columnconfigure(c, weight=1)

            tk.Label(card, text=label, font=('Microsoft YaHei', a.s(10)),
                     bg=t['bg_card'], fg=t['text_sec']).pack()
            lbl = tk.Label(card, text='0本 / 均正确0%', font=('Microsoft YaHei', a.s(11), 'bold'),
                           bg=t['bg_card'], fg=t['text'])
            lbl.pack()
            self._stat_labels[period] = lbl

    def on_enter(self):
        self.refresh()

    def refresh(self):
        t = self.app.theme
        today = datetime.now().strftime('%Y-%m-%d')
        record = get_today_record()

        if record:
            self._today_label.configure(text=f'{today}  已读 {record.book_count} 本  正确率 {int(record.accuracy)}%')
            self._checkin_btn.configure(text='修改')
        else:
            self._today_label.configure(text=f'{today}  今日尚未打卡')
            self._checkin_btn.configure(text='打卡')

        self._update_chart()
        self._update_stats()

    def _update_stats(self):
        for key, days in [('1w', 7), ('1m', 30), ('3m', 90), ('1y', 365)]:
            s = get_stats(days)
            self._stat_labels[key].configure(text=f'{s["total_books"]}本 / 均正确{s["avg_accuracy"]}%')

    def _update_chart(self):
        records = get_recent_records(self._days)
        self._chart.set_records(records)
        t = self.app.theme
        self._chart_label.configure(text='— 绘本数量  — 正确率' if records else '暂无数据')

    def _set_range(self, days):
        self._days = days
        t = self.app.theme
        if days == 7:
            self._btn_7d.configure(bg=t['accent'], fg='white')
            self._btn_30d.configure(bg=t['bg_card'], fg=t['text_sec'])
        else:
            self._btn_7d.configure(bg=t['bg_card'], fg=t['text_sec'])
            self._btn_30d.configure(bg=t['accent'], fg='white')
        self._update_chart()

    def _show_checkin_popup(self):
        t = self.app.theme
        a = self.app
        record = get_today_record()

        popup = tk.Toplevel(self)
        popup.title('绘本打卡')
        popup.geometry(f'{a.sx(380)}x{a.sy(220)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        tk.Label(popup, text='阅读绘本数量', bg=t['bg_card'], fg=t['text'],
                 font=('Microsoft YaHei', a.s(12))).pack(anchor='w', padx=a.sx(20), pady=(a.sy(15), 0))
        count_entry = tk.Entry(popup, font=('Microsoft YaHei', a.s(14)))
        count_entry.pack(fill='x', padx=a.sx(20))
        if record:
            count_entry.insert(0, str(record.book_count))

        tk.Label(popup, text='答题正确率 (如 75 或 5/8)', bg=t['bg_card'], fg=t['text'],
                 font=('Microsoft YaHei', a.s(12))).pack(anchor='w', padx=a.sx(20), pady=(a.sy(10), 0))
        acc_entry = tk.Entry(popup, font=('Microsoft YaHei', a.s(14)))
        acc_entry.pack(fill='x', padx=a.sx(20))
        if record:
            acc_entry.insert(0, str(int(record.accuracy)))

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

        def do_save():
            c = int(count_entry.get().strip()) if count_entry.get().strip() else 0
            acc = _parse_accuracy(acc_entry.get())
            if c > 0:
                upsert_record(c, min(100, max(0, acc)))
            popup.destroy()
            self.refresh()

        btn_frame = tk.Frame(popup, bg=t['bg_card'])
        btn_frame.pack(fill='x', padx=a.sx(20), pady=a.sy(15))
        tk.Button(btn_frame, text='保存', bg=t['accent'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=do_save).pack(side='left', expand=True)
        tk.Button(btn_frame, text='取消', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=popup.destroy).pack(side='left', expand=True)

    def apply_theme(self):
        t = self.app.theme
        self.configure(bg=t['bg'])
        self._chart.configure(bg=t['bg_card'])
        self._update_chart()
