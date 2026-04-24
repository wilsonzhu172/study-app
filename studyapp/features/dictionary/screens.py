import tkinter as tk

from .lookup import lookup_word
from .repository import save_or_update_vocab, get_all_vocab, delete_vocab
from .audio import play_audio
from .models import WordEntry
from ..flashcards.repository import create_card, get_vocab_deck_id


def _bind_touch_scroll(canvas):
    """为 Canvas 绑定触屏拖动滚动"""
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


class DictionaryFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._current_entry = None
        self._history = []
        self._build_ui()

    def _build_ui(self):
        t = self.app.theme
        a = self.app

        # 搜索栏
        search_frame = tk.Frame(self, bg=t['bg'], padx=a.sx(20), pady=a.sy(10))
        search_frame.pack(fill='x')

        self._search_entry = tk.Entry(search_frame, font=('Microsoft YaHei', a.s(16)))
        self._search_entry.pack(side='left', fill='x', expand=True, padx=(0, a.sx(10)))
        self._search_entry.bind('<Return>', lambda e: self._do_search())

        tk.Button(search_frame, text='查询', font=('Microsoft YaHei', a.s(14)),
                  bg=t['accent'], fg='white', relief='flat',
                  command=self._do_search).pack(side='right')

        # 主内容: 左右分栏 (手机上改为上下)
        self._content = tk.Frame(self, bg=t['bg'])
        self._content.pack(fill='both', expand=True, padx=a.sx(20), pady=(0, a.sy(10)))

        is_phone = a.screen_type == 'phone'
        self._content.grid_columnconfigure(0, weight=3 if not is_phone else 1)
        self._content.grid_columnconfigure(1, weight=2 if not is_phone else 1)
        self._content.grid_rowconfigure(0, weight=3 if is_phone else 1)
        self._content.grid_rowconfigure(1, weight=2 if is_phone else 1)

        # 左侧: 单词详情
        left = tk.Frame(self._content, bg=t['bg_card'], highlightbackground=t['border'],
                        highlightthickness=1, padx=a.sx(20), pady=a.sy(15))
        if is_phone:
            left.grid(row=0, column=0, sticky='nsew', pady=(0, a.sy(5)))
        else:
            left.grid(row=0, column=0, sticky='nsew', padx=(0, a.sx(10)))

        word_row = tk.Frame(left, bg=t['bg_card'])
        word_row.pack(fill='x')

        self._result_word = tk.Label(word_row, text='', font=('Microsoft YaHei', a.s(28), 'bold'),
                                     bg=t['bg_card'], fg=t['text'], anchor='w')
        self._result_word.pack(side='left')

        self._result_phonetic = tk.Label(word_row, text='', font=('Microsoft YaHei', a.s(16)),
                                         bg=t['bg_card'], fg=t['text_sec'])
        self._result_phonetic.pack(side='left', padx=a.sx(15))

        tk.Button(word_row, text='播放', font=('Microsoft YaHei', a.s(11)),
                  bg=t['accent'], fg='white', relief='flat',
                  command=self._play_pronunciation).pack(side='right')

        self._result_translation = tk.Label(left, text='', font=('Microsoft YaHei', a.s(18), 'bold'),
                                            bg=t['bg_card'], fg=t['text'], anchor='nw',
                                            wraplength=a.sx(500), justify='left')
        self._result_translation.pack(fill='x', pady=(a.sy(10), a.sy(5)))

        self._result_definition = tk.Label(left, text='', font=('Microsoft YaHei', a.s(13)),
                                           bg=t['bg_card'], fg=t['text_sec'], anchor='nw',
                                           wraplength=a.sx(500), justify='left')
        self._result_definition.pack(fill='x', pady=(0, a.sy(5)))

        self._result_example = tk.Label(left, text='', font=('Microsoft YaHei', a.s(13)),
                                        bg=t['bg_card'], fg=t['accent'], anchor='nw',
                                        wraplength=a.sx(500), justify='left')
        self._result_example.pack(fill='x')

        self._status_label = tk.Label(left, text='', font=('Microsoft YaHei', a.s(11)),
                                      bg=t['bg_card'], fg=t['success'])
        self._status_label.pack(anchor='w', pady=(a.sy(5), 0))

        # 右侧: 搜索历史
        right = tk.Frame(self._content, bg=t['bg_card'], highlightbackground=t['border'],
                         highlightthickness=1, padx=a.sx(15), pady=a.sy(15))
        if is_phone:
            right.grid(row=1, column=0, sticky='nsew')
        else:
            right.grid(row=0, column=1, sticky='nsew')

        tk.Label(right, text='搜索历史', font=('Microsoft YaHei', a.s(15), 'bold'),
                 bg=t['bg_card'], fg=t['text']).pack(anchor='w', pady=(0, a.sy(10)))

        self._history_canvas = tk.Canvas(right, bg=t['bg_card'], highlightthickness=0)
        scrollbar = tk.Scrollbar(right, orient='vertical', command=self._history_canvas.yview)
        self._history_frame = tk.Frame(self._history_canvas, bg=t['bg_card'])
        self._history_frame.bind('<Configure>',
            lambda e: self._history_canvas.configure(scrollregion=self._history_canvas.bbox('all')))
        self._history_canvas.create_window((0, 0), window=self._history_frame, anchor='nw')
        self._history_canvas.configure(yscrollcommand=scrollbar.set)
        self._history_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        _bind_touch_scroll(self._history_canvas)

    def _do_search(self, word=None):
        if word is None:
            word = self._search_entry.get().strip()
        if not word:
            return
        self._search_entry.delete(0, tk.END)
        self._search_entry.insert(0, word)

        self._result_word.configure(text='查询中...')
        for lbl in (self._result_phonetic, self._result_translation,
                    self._result_definition, self._result_example, self._status_label):
            lbl.configure(text='')
        self.update()

        entry = lookup_word(word)
        self._current_entry = entry

        if not entry.translation and not entry.definition:
            self._result_word.configure(text=f'未找到: {word}')
            return

        self._result_word.configure(text=entry.word)
        self._result_phonetic.configure(text=entry.phonetic)
        self._result_translation.configure(text=entry.translation or '')
        self._result_definition.configure(text=entry.definition or '')
        self._result_example.configure(text=f'例句: {entry.example}' if entry.example else '')
        self._add_history(entry.word)
        self._save_to_vocab(entry)
        self._status_label.configure(text='已加入生词本')

    def _save_to_vocab(self, entry: WordEntry):
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

        from ..flashcards.repository import get_daily_deck_id, add_to_daily_deck
        daily_id = get_daily_deck_id()
        if daily_id:
            add_to_daily_deck(daily_id, entry.word, back)

    def _add_history(self, word):
        self._history = [w for w in self._history if w != word]
        self._history.insert(0, word)

        t = self.app.theme
        a = self.app
        for w in self._history_frame.winfo_children():
            w.destroy()
        for w in self._history:
            btn = tk.Button(self._history_frame, text=w, font=('Microsoft YaHei', a.s(13)),
                           bg=t['accent_light'], fg=t['accent'], relief='flat', anchor='w',
                           command=lambda word=w: self._do_search(word))
            btn.pack(fill='x', pady=a.sy(2))

    def _play_pronunciation(self):
        if not self._current_entry or not self._current_entry.audio_url:
            self._status_label.configure(text='暂无音频')
            return
        self._status_label.configure(text='播放中...')
        play_audio(self._current_entry.audio_url, on_stop=lambda: self._status_label.configure(text=''))

    def on_enter(self):
        pass

    def apply_theme(self):
        t = self.app.theme
        self.configure(bg=t['bg'])


class VocabListFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        t = self.app.theme
        a = self.app

        tk.Label(self, text='我的生词本', font=('Microsoft YaHei', a.s(22), 'bold'),
                 bg=t['bg'], fg=t['text']).pack(anchor='w', padx=a.sx(20), pady=(a.sy(15), a.sy(10)))

        # 表头
        header = tk.Frame(self, bg=t['bg_card'], highlightbackground=t['border'],
                         highlightthickness=1, padx=a.sx(10), pady=a.sy(8))
        header.pack(fill='x', padx=a.sx(20))

        is_phone = a.screen_type == 'phone'
        if not is_phone:
            for text, w in [('单词', 15), ('音标', 12), ('释义', 35), ('次数', 6)]:
                tk.Label(header, text=text, font=('Microsoft YaHei', a.s(13), 'bold'),
                         bg=t['bg_card'], fg=t['text'], width=w, anchor='w').pack(side='left')
        else:
            for text in [('单词', 20), ('释义', 30)]:
                tk.Label(header, text=text[0], font=('Microsoft YaHei', a.s(13), 'bold'),
                         bg=t['bg_card'], fg=t['text'], anchor='w').pack(side='left', fill='x', expand=True)

        # 可滚动列表
        self._canvas = tk.Canvas(self, highlightthickness=0, bg=t['bg'])
        self._canvas.pack(fill='both', expand=True, padx=a.sx(20), pady=(a.sy(5), a.sy(10)))

        self._vocab_container = tk.Frame(self._canvas, bg=t['bg'])
        self._canvas_window = self._canvas.create_window((0, 0), window=self._vocab_container, anchor='nw')
        self._vocab_container.bind('<Configure>',
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfig(
            self._canvas_window, width=e.width))
        self._canvas.bind('<Enter>',
            lambda e: self._canvas.bind_all('<MouseWheel>',
                lambda ev: self._canvas.yview_scroll(-1 * (ev.delta // 120), 'units')))
        self._canvas.bind('<Leave>', lambda e: self._canvas.unbind_all('<MouseWheel>'))
        _bind_touch_scroll(self._canvas)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        for w in self._vocab_container.winfo_children():
            w.destroy()
        t = self.app.theme
        a = self.app
        is_phone = a.screen_type == 'phone'

        from studyapp.core.database import get_connection
        rows = get_connection().execute(
            "SELECT word, phonetic, translation, lookup_count FROM vocabulary ORDER BY created_at DESC"
        ).fetchall()

        for r in rows:
            row = tk.Frame(self._vocab_container, bg=t['bg_card'], highlightbackground=t['border'],
                          highlightthickness=1, padx=a.sx(10), pady=a.sy(6))
            row.pack(fill='x', pady=a.sy(2))

            if is_phone:
                tk.Label(row, text=r['word'], font=('Microsoft YaHei', a.s(13)),
                         bg=t['bg_card'], fg=t['text'], anchor='w').pack(side='left', fill='x', expand=True)
                translation = (r['translation'] or '')[:25]
                tk.Label(row, text=translation, font=('Microsoft YaHei', a.s(11)),
                         bg=t['bg_card'], fg=t['text_sec'], anchor='w').pack(side='left', padx=a.sx(5))
            else:
                tk.Label(row, text=r['word'], font=('Microsoft YaHei', a.s(13)),
                         bg=t['bg_card'], fg=t['text'], width=15, anchor='w').pack(side='left')
                tk.Label(row, text=r['phonetic'], font=('Microsoft YaHei', a.s(12)),
                         bg=t['bg_card'], fg=t['text_sec'], width=12, anchor='w').pack(side='left')
                translation = (r['translation'] or '')[:40]
                tk.Label(row, text=translation, font=('Microsoft YaHei', a.s(12)),
                         bg=t['bg_card'], fg=t['text_sec'], width=35, anchor='w').pack(side='left')
                tk.Label(row, text=str(r['lookup_count']), font=('Microsoft YaHei', a.s(12)),
                         bg=t['bg_card'], fg=t['text_sec'], width=6).pack(side='left')

            tk.Button(row, text='删除', font=('Microsoft YaHei', a.s(10)),
                      bg=t['danger'], fg='white', relief='flat',
                      command=lambda w=r['word']: [delete_vocab(w), self.refresh()]).pack(side='right')

    def apply_theme(self):
        t = self.app.theme
        self.configure(bg=t['bg'])
        self._canvas.configure(bg=t['bg'])
        self._vocab_container.configure(bg=t['bg'])
