import tkinter as tk

from .repository import (
    get_decks, get_deck, create_deck, delete_deck,
    get_cards_by_deck, get_card, create_card, update_card, delete_card,
    get_card_count, get_learned_count, get_preset_decks, import_preset_deck,
    update_deck_daily_limit, is_deck_checked_in,
)
from .study_engine import get_study_cards, process_grade
from .repository import add_study_record, get_vocab_deck_id, checkin_deck, get_due_cards, get_new_cards


def _deck_columns(app):
    """根据屏幕宽度决定牌组网格列数"""
    w = app.win_size[0]
    if w < 500:
        return 1
    elif w < 900:
        return 2
    else:
        return 3


def _bind_touch_scroll(canvas):
    """为 Canvas 绑定触屏拖动滚动 (平板/手机适用)"""
    state = {'y': 0}

    def _press(e):
        state['y'] = e.y

    def _drag(e):
        dy = e.y - state['y']
        if abs(dy) > 3:
            canvas.yview_scroll(int(-dy / 3), 'units')
            state['y'] = e.y

    canvas.bind('<ButtonPress-1>', _press, add='+')
    canvas.bind('<B1-Motion>', _drag, add='+')


class DeckListFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        t = self.app.theme

        header = tk.Frame(self, bg=t['bg'])
        header.pack(fill='x', padx=self.app.sx(20), pady=(self.app.sy(15), self.app.sy(10)))

        tk.Label(header, text='我的牌组', font=('Microsoft YaHei', self.app.s(22), 'bold'),
                 bg=t['bg'], fg=t['text']).pack(side='left')

        tk.Button(header, text='+ 新建牌组', font=('Microsoft YaHei', self.app.s(12)),
                  bg=t['accent'], fg='white', relief='flat',
                  command=self._show_add_deck).pack(side='right', padx=(self.app.sx(10), 0))
        tk.Button(header, text='导入牌组', font=('Microsoft YaHei', self.app.s(12)),
                  bg=t['success'], fg='white', relief='flat',
                  command=self._show_import_deck).pack(side='right')

        # 可滚动区域
        self._scroll_canvas = tk.Canvas(self, highlightthickness=0, bg=t['bg'])
        self._scroll_canvas.pack(fill='both', expand=True, padx=self.app.sx(20), pady=(0, self.app.sy(10)))

        self._deck_container = tk.Frame(self._scroll_canvas, bg=t['bg'])
        self._window_id = self._scroll_canvas.create_window((0, 0), window=self._deck_container, anchor='nw')

        self._deck_container.bind('<Configure>',
            lambda e: self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox('all')))
        self._scroll_canvas.bind('<Configure>', self._on_canvas_resize)
        self._scroll_canvas.bind('<Enter>',
            lambda e: self._scroll_canvas.bind_all('<MouseWheel>',
                lambda ev: self._scroll_canvas.yview_scroll(-1 * (ev.delta // 120), 'units')))
        self._scroll_canvas.bind('<Leave>', lambda e: self._scroll_canvas.unbind_all('<MouseWheel>'))
        _bind_touch_scroll(self._scroll_canvas)

    def _on_canvas_resize(self, event):
        self._scroll_canvas.itemconfig(self._window_id, width=event.width)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        for w in self._deck_container.winfo_children():
            w.destroy()

        t = self.app.theme
        cols = _deck_columns(self.app)
        decks = get_decks()

        for i, deck in enumerate(decks):
            row, col = divmod(i, cols)
            self._create_deck_tile(deck, row, col, cols)

    def _create_deck_tile(self, deck, row, col, cols):
        t = self.app.theme
        a = self.app
        total = get_card_count(deck.id)
        learned = get_learned_count(deck.id)
        pct = int(learned / total * 100) if total else 0

        tile = tk.Frame(self._deck_container, bg=t['bg_card'], highlightbackground=t['border'],
                        highlightthickness=1, padx=a.sx(15), pady=a.sy(10))
        tile.grid(row=row, column=col, padx=a.sx(10), pady=a.sy(8), sticky='nsew')
        for c in range(cols):
            self._deck_container.grid_columnconfigure(c, weight=1)

        # 色条
        tk.Frame(tile, bg=deck.color, height=a.sy(4)).pack(fill='x', pady=(0, a.sy(5)))

        # 名称
        tk.Label(tile, text=deck.name, font=('Microsoft YaHei', a.s(16), 'bold'),
                 bg=t['bg_card'], fg=t['text'], anchor='w').pack(fill='x')

        # 描述
        desc = deck.description or f'{total}张卡片'
        tk.Label(tile, text=desc, font=('Microsoft YaHei', a.s(11)),
                 bg=t['bg_card'], fg=t['text_sec'], anchor='w').pack(fill='x')

        # 进度
        tk.Label(tile, text=f'掌握 {pct}% ({learned}/{total})', font=('Microsoft YaHei', a.s(11)),
                 bg=t['bg_card'], fg=t['accent'], anchor='w').pack(fill='x')

        # 设置 + 打卡
        info_frame = tk.Frame(tile, bg=t['bg_card'])
        info_frame.pack(fill='x', pady=(a.sy(2), 0))

        limit_text = '' if deck.is_system == 2 else f'每日新卡: {deck.daily_new_limit}'
        limit_lbl = tk.Label(info_frame, text=limit_text, font=('Microsoft YaHei', a.s(9)),
                             bg=t['bg_card'], fg=t['text_sec'], anchor='w')
        limit_lbl.pack(side='left')
        if limit_text:
            limit_lbl.bind('<Button-1>', lambda e, d=deck.id: self._show_deck_settings(d))

        if is_deck_checked_in(deck.id):
            tk.Label(info_frame, text='已打卡', font=('Microsoft YaHei', a.s(9), 'bold'),
                     bg=t['bg_card'], fg=t['success']).pack(side='right')

        # 操作按钮
        btn_frame = tk.Frame(tile, bg=t['bg_card'])
        btn_frame.pack(fill='x', pady=(a.sy(5), 0))
        btn_font = ('Microsoft YaHei', a.s(11))

        tk.Button(btn_frame, text='学习', font=btn_font, bg=t['accent'], fg='white',
                  relief='flat', command=lambda d=deck.id: self._study_deck(d)).pack(side='left', padx=(0, a.sx(5)))
        tk.Button(btn_frame, text='编辑', font=btn_font, bg=t['warning'], fg='white',
                  relief='flat', command=lambda d=deck.id: self._edit_cards(d)).pack(side='left', padx=(0, a.sx(5)))

        if deck.is_system:
            tk.Button(btn_frame, text='删卡', font=btn_font, bg=t['danger'], fg='white',
                      relief='flat', command=lambda d=deck.id: self._batch_delete(d)).pack(side='left')
        else:
            tk.Button(btn_frame, text='删除', font=btn_font, bg=t['danger'], fg='white',
                      relief='flat', command=lambda d=deck.id: self._confirm_delete(d)).pack(side='left')

    def _study_deck(self, deck_id):
        self.app.show_sub_screen('study', deck_id=deck_id)

    def _edit_cards(self, deck_id):
        self.app.show_sub_screen('card_editor', deck_id=deck_id)

    def _confirm_delete(self, deck_id):
        t = self.app.theme
        a = self.app
        popup = tk.Toplevel(self)
        popup.title('确认删除')
        popup.geometry(f'{a.sx(300)}x{a.sy(150)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        tk.Label(popup, text='确定删除这个牌组？', font=('Microsoft YaHei', a.s(14)),
                 bg=t['bg_card'], fg=t['text']).pack(expand=True)

        btn_frame = tk.Frame(popup, bg=t['bg_card'])
        btn_frame.pack(fill='x', padx=a.sx(20), pady=a.sy(10))
        tk.Button(btn_frame, text='删除', bg=t['danger'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)),
                  command=lambda: [delete_deck(deck_id), popup.destroy(), self.refresh()]).pack(side='left', expand=True)
        tk.Button(btn_frame, text='取消', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)),
                  command=popup.destroy).pack(side='left', expand=True)

    def _batch_delete(self, deck_id):
        cards = get_cards_by_deck(deck_id)
        if not cards:
            return
        t = self.app.theme
        a = self.app
        popup = tk.Toplevel(self)
        popup.title('选择要删除的卡片')
        popup.geometry(f'{a.sx(500)}x{a.sy(400)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        canvas = tk.Canvas(popup, bg=t['bg_card'], highlightthickness=0)
        scrollbar = tk.Scrollbar(popup, orient='vertical', command=canvas.yview)
        inner = tk.Frame(canvas, bg=t['bg_card'])
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True, padx=a.sx(10), pady=a.sy(10))
        scrollbar.pack(side='right', fill='y')

        checkboxes = []
        for card in cards:
            var = tk.BooleanVar()
            text = card.front if len(card.front) <= 25 else card.front[:25] + '...'
            tk.Checkbutton(inner, text=text, variable=var, bg=t['bg_card'], fg=t['text'],
                           selectcolor=t['bg_card'], activebackground=t['bg_card'],
                           font=('Microsoft YaHei', a.s(12))).pack(anchor='w', pady=a.sy(2))
            checkboxes.append((var, card.id))

        btn_frame = tk.Frame(popup, bg=t['bg_card'])
        btn_frame.pack(fill='x', padx=a.sx(20), pady=a.sy(10))
        tk.Button(btn_frame, text='删除选中', bg=t['danger'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)),
                  command=lambda: [self._do_batch_delete(checkboxes), popup.destroy()]).pack(side='left', expand=True)
        tk.Button(btn_frame, text='取消', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)),
                  command=popup.destroy).pack(side='left', expand=True)

    def _do_batch_delete(self, checkboxes):
        for var, cid in checkboxes:
            if var.get():
                delete_card(cid)
        self.refresh()

    def _show_add_deck(self):
        t = self.app.theme
        a = self.app
        popup = tk.Toplevel(self)
        popup.title('新建牌组')
        popup.geometry(f'{a.sx(400)}x{a.sy(300)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        entries = {}
        for label, default in [('牌组名称', ''), ('描述(可选)', ''), ('颜色(如 #2196F3)', ''), ('每日新卡数量(默认20)', '20')]:
            tk.Label(popup, text=label, bg=t['bg_card'], fg=t['text'],
                     font=('Microsoft YaHei', a.s(12))).pack(anchor='w', padx=a.sx(20), pady=(a.sy(10), 0))
            entry = tk.Entry(popup, font=('Microsoft YaHei', a.s(14)))
            entry.insert(0, default)
            entry.pack(fill='x', padx=a.sx(20))
            entries[label] = entry

        def do_create():
            name = entries['牌组名称'].get().strip()
            if name:
                limit = int(entries['每日新卡数量(默认20)'].get().strip() or '20')
                create_deck(name, entries['描述(可选)'].get().strip(),
                           entries['颜色(如 #2196F3)'].get().strip() or '#4CAF50', limit)
                popup.destroy()
                self.refresh()

        btn_frame = tk.Frame(popup, bg=t['bg_card'])
        btn_frame.pack(fill='x', padx=a.sx(20), pady=a.sy(15))
        tk.Button(btn_frame, text='确定', bg=t['accent'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=do_create).pack(side='left', expand=True)
        tk.Button(btn_frame, text='取消', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=popup.destroy).pack(side='left', expand=True)

    def _show_deck_settings(self, deck_id):
        t = self.app.theme
        a = self.app
        deck = get_deck(deck_id)
        popup = tk.Toplevel(self)
        popup.title('牌组设置')
        popup.geometry(f'{a.sx(350)}x{a.sy(180)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        tk.Label(popup, text=f'牌组: {deck.name}', bg=t['bg_card'], fg=t['text'],
                 font=('Microsoft YaHei', a.s(14))).pack(pady=(a.sy(15), a.sy(5)))
        tk.Label(popup, text='每日新卡数量', bg=t['bg_card'], fg=t['text'],
                 font=('Microsoft YaHei', a.s(11))).pack()
        entry = tk.Entry(popup, font=('Microsoft YaHei', a.s(14)))
        entry.insert(0, str(deck.daily_new_limit))
        entry.pack(padx=a.sx(20))

        def do_save():
            val = int(entry.get().strip() or '20')
            update_deck_daily_limit(deck_id, max(1, val))
            popup.destroy()
            self.refresh()

        btn_frame = tk.Frame(popup, bg=t['bg_card'])
        btn_frame.pack(fill='x', padx=a.sx(20), pady=a.sy(15))
        tk.Button(btn_frame, text='保存', bg=t['accent'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=do_save).pack(side='left', expand=True)
        tk.Button(btn_frame, text='取消', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=popup.destroy).pack(side='left', expand=True)

    def _show_import_deck(self):
        presets = get_preset_decks()
        if not presets:
            return
        t = self.app.theme
        a = self.app
        popup = tk.Toplevel(self)
        popup.title('导入预设牌组')
        popup.geometry(f'{a.sx(600)}x{a.sy(400)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        canvas = tk.Canvas(popup, bg=t['bg_card'], highlightthickness=0)
        scrollbar = tk.Scrollbar(popup, orient='vertical', command=canvas.yview)
        inner = tk.Frame(canvas, bg=t['bg_card'])
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True, padx=a.sx(10), pady=a.sy(10))
        scrollbar.pack(side='right', fill='y')

        for p in presets:
            row = tk.Frame(inner, bg=t['bg_card'], pady=a.sy(8))
            row.pack(fill='x', padx=a.sx(10))
            tk.Label(row, text='██', fg=p['color'], bg=t['bg_card'],
                     font=('Microsoft YaHei', a.s(14))).pack(side='left')
            tk.Label(row, text=p['name'], bg=t['bg_card'], fg=t['text'],
                     font=('Microsoft YaHei', a.s(14), 'bold')).pack(side='left', padx=a.sx(5))
            tk.Label(row, text=f"{p['description']}  ({p['card_count']}张)",
                     bg=t['bg_card'], fg=t['text_sec'],
                     font=('Microsoft YaHei', a.s(11))).pack(side='left', padx=a.sx(5))
            if p['imported']:
                tk.Label(row, text='已导入', bg=t['bg_card'], fg=t['text_sec'],
                         font=('Microsoft YaHei', a.s(11))).pack(side='right')
            else:
                tk.Button(row, text='导入', bg=t['accent'], fg='white', relief='flat',
                          font=('Microsoft YaHei', a.s(12)),
                          command=lambda pid=p['id']: [import_preset_deck(pid), popup.destroy(), self.refresh()]
                          ).pack(side='right')

        tk.Button(popup, text='关闭', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)),
                  command=popup.destroy).pack(pady=a.sy(10))

    def apply_theme(self):
        t = self.app.theme
        self.configure(bg=t['bg'])
        self._scroll_canvas.configure(bg=t['bg'])
        self._deck_container.configure(bg=t['bg'])


class CardEditorFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._deck_id = None
        self._build_ui()

    def _build_ui(self):
        t = self.app.theme
        a = self.app

        header = tk.Frame(self, bg=t['bg'])
        header.pack(fill='x', padx=a.sx(20), pady=a.sy(10))

        tk.Button(header, text='< 返回', font=('Microsoft YaHei', a.s(12)),
                  bg=t['accent'], fg='white', relief='flat',
                  command=self._go_back).pack(side='left')

        self._title_label = tk.Label(header, text='编辑牌组',
                                     font=('Microsoft YaHei', a.s(18), 'bold'),
                                     bg=t['bg'], fg=t['text'])
        self._title_label.pack(side='left', padx=a.sx(20))

        tk.Button(header, text='+ 添加卡片', font=('Microsoft YaHei', a.s(12)),
                  bg=t['accent'], fg='white', relief='flat',
                  command=self._show_add_card).pack(side='right')

        self._canvas = tk.Canvas(self, highlightthickness=0, bg=t['bg'])
        self._canvas.pack(fill='both', expand=True, padx=a.sx(20), pady=(0, a.sy(10)))

        self._card_container = tk.Frame(self._canvas, bg=t['bg'])
        self._canvas_window = self._canvas.create_window((0, 0), window=self._card_container, anchor='nw')
        self._card_container.bind('<Configure>',
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfig(
            self._canvas_window, width=e.width))
        self._canvas.bind('<Enter>',
            lambda e: self._canvas.bind_all('<MouseWheel>',
                lambda ev: self._canvas.yview_scroll(-1 * (ev.delta // 120), 'units')))
        self._canvas.bind('<Leave>', lambda e: self._canvas.unbind_all('<MouseWheel>'))
        _bind_touch_scroll(self._canvas)

    def load(self, deck_id=None, **kwargs):
        if deck_id is not None:
            self._deck_id = deck_id
        self.refresh()

    def on_enter(self):
        if self._deck_id:
            self.refresh()

    def refresh(self):
        for w in self._card_container.winfo_children():
            w.destroy()
        t = self.app.theme
        a = self.app
        deck = get_deck(self._deck_id)
        self._title_label.configure(text=f'编辑: {deck.name}')

        is_phone = a.screen_type == 'phone'

        for card in get_cards_by_deck(self._deck_id):
            row = tk.Frame(self._card_container, bg=t['bg_card'], highlightbackground=t['border'],
                          highlightthickness=1, padx=a.sx(10), pady=a.sy(8))
            row.pack(fill='x', pady=a.sy(4))

            front = card.front if len(card.front) <= 20 else card.front[:20] + '...'
            back = card.back if len(card.back) <= 30 else card.back[:30] + '...'

            if is_phone:
                # 手机: 纵向排列
                tk.Label(row, text=front, bg=t['bg_card'], fg=t['text'],
                         font=('Microsoft YaHei', a.s(12)), anchor='w').pack(fill='x')
                tk.Label(row, text=back, bg=t['bg_card'], fg=t['text_sec'],
                         font=('Microsoft YaHei', a.s(11)), anchor='w').pack(fill='x')
            else:
                tk.Label(row, text=front, bg=t['bg_card'], fg=t['text'],
                         font=('Microsoft YaHei', a.s(12)), anchor='w').pack(side='left', fill='x', expand=True)
                tk.Label(row, text=back, bg=t['bg_card'], fg=t['text_sec'],
                         font=('Microsoft YaHei', a.s(11)), anchor='w').pack(side='left', fill='x', expand=True)

            tk.Button(row, text='编辑', bg=t['warning'], fg='white', relief='flat',
                      font=('Microsoft YaHei', a.s(10)),
                      command=lambda c=card.id: self._edit_card(c)).pack(side='right', padx=a.sx(2))
            tk.Button(row, text='删除', bg=t['danger'], fg='white', relief='flat',
                      font=('Microsoft YaHei', a.s(10)),
                      command=lambda c=card.id: [delete_card(c), self.refresh()]).pack(side='right', padx=a.sx(2))

    def _show_add_card(self):
        self._show_card_dialog()

    def _edit_card(self, card_id):
        card = get_card(card_id)
        if card:
            self._show_card_dialog(card)

    def _show_card_dialog(self, card=None):
        t = self.app.theme
        a = self.app
        popup = tk.Toplevel(self)
        popup.title('编辑卡片' if card else '添加卡片')
        popup.geometry(f'{a.sx(450)}x{a.sy(250)}')
        popup.configure(bg=t['bg_card'])
        popup.transient(self)
        popup.grab_set()

        tk.Label(popup, text='正面 (问题)', bg=t['bg_card'], fg=t['text'],
                 font=('Microsoft YaHei', a.s(12))).pack(anchor='w', padx=a.sx(20), pady=(a.sy(15), 0))
        front_entry = tk.Entry(popup, font=('Microsoft YaHei', a.s(14)))
        front_entry.pack(fill='x', padx=a.sx(20))
        if card:
            front_entry.insert(0, card.front)

        tk.Label(popup, text='背面 (答案)', bg=t['bg_card'], fg=t['text'],
                 font=('Microsoft YaHei', a.s(12))).pack(anchor='w', padx=a.sx(20), pady=(a.sy(10), 0))
        back_entry = tk.Entry(popup, font=('Microsoft YaHei', a.s(14)))
        back_entry.pack(fill='x', padx=a.sx(20))
        if card:
            back_entry.insert(0, card.back)

        def do_save():
            f = front_entry.get().strip()
            b = back_entry.get().strip()
            if f and b:
                if card:
                    update_card(card.id, f, b)
                else:
                    create_card(self._deck_id, f, b)
                popup.destroy()
                self.refresh()

        btn_frame = tk.Frame(popup, bg=t['bg_card'])
        btn_frame.pack(fill='x', padx=a.sx(20), pady=a.sy(15))
        tk.Button(btn_frame, text='保存', bg=t['accent'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=do_save).pack(side='left', expand=True)
        tk.Button(btn_frame, text='取消', bg=t['text_sec'], fg='white', relief='flat',
                  font=('Microsoft YaHei', a.s(12)), command=popup.destroy).pack(side='left', expand=True)

    def _go_back(self):
        self.app.show_tab('flashcards')

    def apply_theme(self):
        t = self.app.theme
        self.configure(bg=t['bg'])
        self._canvas.configure(bg=t['bg'])
        self._card_container.configure(bg=t['bg'])


class StudyFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._cards = []
        self._index = 0
        self._total = 0
        self._flipped = False
        self._is_daily = False
        self._deck_id = None
        self._card_scroll_active = False
        self._build_ui()

    def _build_ui(self):
        t = self.app.theme
        a = self.app

        header = tk.Frame(self, bg=t['bg'])
        header.pack(fill='x', padx=a.sx(20), pady=a.sy(10))

        tk.Button(header, text='< 返回', font=('Microsoft YaHei', a.s(12)),
                  bg=t['accent'], fg='white', relief='flat',
                  command=self._go_back).pack(side='left')

        self._study_title = tk.Label(header, text='学习',
                                     font=('Microsoft YaHei', a.s(18), 'bold'),
                                     bg=t['bg'], fg=t['text'])
        self._study_title.pack(side='left', padx=a.sx(20))

        self._progress_label = tk.Label(header, text='0/0',
                                        font=('Microsoft YaHei', a.s(14)),
                                        bg=t['bg'], fg=t['text_sec'])
        self._progress_label.pack(side='right')

        # 卡片区域 (外框 + 内部可滚动)
        self._card_frame = tk.Frame(self, bg=t['bg'], padx=a.sx(40), pady=a.sy(20))
        self._card_frame.pack(fill='both', expand=True)

        self._card_box = tk.Frame(self._card_frame, bg=t['bg_card'], highlightbackground=t['border'],
                                  highlightthickness=2)
        self._card_box.place(relx=0.5, rely=0.45, anchor='center', relwidth=0.6, relheight=0.6)

        # 可滚动的卡片内容区
        self._card_canvas = tk.Canvas(self._card_box, bg=t['bg_card'], highlightthickness=0)
        self._card_scrollbar = tk.Scrollbar(self._card_box, orient='vertical',
                                            command=self._card_canvas.yview)
        self._card_inner = tk.Frame(self._card_canvas, bg=t['bg_card'])
        self._card_inner.bind('<Configure>',
            lambda e: self._card_canvas.configure(scrollregion=self._card_canvas.bbox('all')))
        self._card_canvas_window = self._card_canvas.create_window(
            (0, 0), window=self._card_inner, anchor='nw', tags='inner')
        self._card_canvas.configure(yscrollcommand=self._on_card_scroll)

        self._card_canvas.pack(side='left', fill='both', expand=True, padx=a.sx(30), pady=a.sy(30))
        self._card_scrollbar.pack(side='right', fill='y')

        # Canvas 宽度随容器变化
        self._card_canvas.bind('<Configure>',
            lambda e: self._card_canvas.itemconfig('inner', width=e.width))

        # 鼠标滚轮 (仅在卡片区域内生效)
        self._card_canvas.bind('<Enter>', self._bind_card_wheel)
        self._card_canvas.bind('<Leave>',
            lambda e: self._card_canvas.unbind_all('<MouseWheel>'))

        self._card_label = tk.Label(self._card_inner, text='',
                                    font=('Microsoft YaHei', a.s(28), 'bold'),
                                    bg=t['bg_card'], fg=t['text'], wraplength=a.sx(500),
                                    justify='center')
        self._card_label.pack(fill='x', padx=a.sx(10), pady=a.sy(10))

        # 触屏拖动滚动 + 点击翻转 (区分拖动与点击)
        self._touch_start_y = 0
        self._touch_dragged = False
        self._card_canvas.bind('<ButtonPress-1>', self._on_touch_press)
        self._card_canvas.bind('<B1-Motion>', self._on_touch_drag)
        self._card_canvas.bind('<ButtonRelease-1>', self._on_touch_release)
        self._card_label.bind('<Button-1>', lambda e: self._flip_card())

        self._hint_label = tk.Label(self, text='点击卡片查看答案',
                                    font=('Microsoft YaHei', a.s(12)),
                                    bg=t['bg'], fg=t['text_sec'])
        self._hint_label.pack(pady=(a.sy(5), a.sy(10)))

        # 评分按钮
        btn_frame = tk.Frame(self, bg=t['bg'])
        btn_frame.pack(pady=(0, a.sy(20)))

        self._grade_buttons = []
        for grade, (text, color) in enumerate([('重来', 'danger'), ('困难', 'warning'),
                                                ('良好', 'success'), ('简单', 'accent')]):
            btn = tk.Button(btn_frame, text=text, font=('Microsoft YaHei', a.s(14)),
                           bg=t[color], fg='white', relief='flat', width=8,
                           state='disabled',
                           command=lambda g=grade: self._grade_card(g))
            btn.pack(side='left', padx=a.sx(15))
            self._grade_buttons.append((btn, grade, color))

    def _on_card_scroll(self, first, last):
        first, last = float(first), float(last)
        self._card_scrollbar.set(first, last)
        visible = not (first <= 0.0 and last >= 1.0)
        if visible != self._card_scroll_active:
            self._card_scroll_active = visible
            if visible:
                self._card_scrollbar.pack(side='right', fill='y')
            else:
                self._card_scrollbar.pack_forget()

    def _bind_card_wheel(self, event):
        def _on_wheel(ev):
            if self._card_scroll_active:
                self._card_canvas.yview_scroll(-1 * (ev.delta // 120), 'units')
        self._card_canvas.bind_all('<MouseWheel>', _on_wheel)

    def _on_touch_press(self, event):
        self._touch_start_y = event.y
        self._touch_dragged = False

    def _on_touch_drag(self, event):
        dy = event.y - self._touch_start_y
        if abs(dy) > 5:
            self._touch_dragged = True
            self._card_canvas.yview_scroll(int(-dy / 3), 'units')
            self._touch_start_y = event.y

    def _on_touch_release(self, event):
        if not self._touch_dragged:
            self._flip_card()

    def load(self, deck_id=None, **kwargs):
        if deck_id is not None:
            self._deck_id = deck_id
            deck = get_deck(deck_id)
            self._study_title.configure(text=deck.name)
            self._is_daily = deck.is_system == 2
            if self._is_daily:
                self._cards = get_new_cards(deck_id) + get_due_cards(deck_id)
            else:
                self._cards = get_study_cards(deck_id, deck.daily_new_limit)
            self._index = 0
            self._total = len(self._cards)
            self._show_card()

    def _show_card(self):
        t = self.app.theme
        if self._index >= len(self._cards):
            if self._is_daily:
                remaining = get_due_cards(self._deck_id)
                if remaining:
                    self._cards = remaining
                    self._index = 0
                    card = self._cards[self._index]
                    self._flipped = False
                    self._card_label.configure(text=card.front)
                    self._hint_label.configure(text='点击卡片查看答案 (未掌握，继续循环)')
                    mastered = self._total - len(remaining)
                    self._progress_label.configure(text=f'已掌握 {mastered}/{self._total}')
                    self._card_box.configure(bg=t['bg_card'])
                    self._set_buttons_enabled(False)
                    return

            self._card_label.configure(text='全部学完！')
            self._hint_label.configure(text='')
            self._progress_label.configure(text=f'已学 {self._total}/{self._total}')
            if self._total > 0:
                checkin_deck(self._deck_id)
            self._set_buttons_enabled(False)
            return

        card = self._cards[self._index]
        self._flipped = False
        self._card_label.configure(text=card.front)
        self._hint_label.configure(text='点击卡片查看答案')
        self._progress_label.configure(text=f'已学 {self._index}/{self._total}')
        self._card_box.configure(bg=t['bg_card'])
        self._set_buttons_enabled(False)

    def _flip_card(self):
        if self._flipped or self._index >= len(self._cards):
            return
        self._flipped = True
        card = self._cards[self._index]
        self._card_label.configure(text=card.back)
        self._hint_label.configure(text='为这张卡片评分')
        self._set_buttons_enabled(True)

    def _grade_card(self, grade):
        if self._index >= len(self._cards):
            return
        t = self.app.theme
        card = self._cards[self._index]
        add_study_record(card.id, grade)

        if self._is_daily:
            from datetime import datetime, timedelta
            if grade >= 2:
                new_level, next_review = 5, (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                new_level, next_review = 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            from .repository import upsert_card_progress
            upsert_card_progress(card.id, new_level, next_review)
        else:
            progress = process_grade(card.id, grade)
            if progress and progress['level'] >= 5:
                vocab_deck_id = get_vocab_deck_id()
                if vocab_deck_id and card.deck_id == vocab_deck_id:
                    from ..dictionary.repository import delete_vocab_by_card_id
                    delete_vocab_by_card_id(card.id)

        colors = {0: '#EF4444', 1: '#F97316', 2: '#14B8A6', 3: '#6366F1'}
        self._card_box.configure(bg=colors.get(grade, t['bg_card']))
        self._index += 1
        self.after(500, self._show_card)

    def _set_buttons_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        for btn, _, _ in self._grade_buttons:
            btn.configure(state=state)

    def _go_back(self):
        self.app.show_tab('flashcards')

    def apply_theme(self):
        t = self.app.theme
        self.configure(bg=t['bg'])
        self._card_frame.configure(bg=t['bg'])
        self._card_canvas.configure(bg=t['bg_card'])
        self._card_inner.configure(bg=t['bg_card'])
        self._card_label.configure(bg=t['bg_card'], fg=t['text'])
        self._hint_label.configure(bg=t['bg'], fg=t['text_sec'])
        self._progress_label.configure(bg=t['bg'], fg=t['text_sec'])
        self._study_title.configure(bg=t['bg'], fg=t['text'])
        for btn, grade, color in self._grade_buttons:
            btn.configure(bg=t[color])
