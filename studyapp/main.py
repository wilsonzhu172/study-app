import tkinter as tk
from tkinter import font as tkfont

from studyapp.core.database import init_db
from studyapp.core.theme import LIGHT, DARK

# 基准分辨率 (设计参考)
_REF_W, _REF_H = 1280, 720


class StudyApp(tk.Tk):
    """学习助手主应用 - 自适应屏幕"""

    def __init__(self):
        super().__init__()
        self.title('学习助手')

        init_db()

        self._is_dark = False
        self._theme = LIGHT
        self._active_tab = 'flashcards'

        # 屏幕检测与缩放
        self._detect_screen()
        self._setup_fonts()

        self._build_ui()
        self._init_frames()
        self.show_tab('flashcards')

    @property
    def theme(self):
        return self._theme

    def _detect_screen(self):
        """检测屏幕尺寸, 计算缩放因子"""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # 设置窗口: 小屏全屏, 大屏居中
        if sw <= 1080:
            self.geometry(f'{sw}x{sh}+0+0')
            self.attributes('-fullscreen', True)
        else:
            w, h = min(sw, 1920), min(sh, 1080)
            x = (sw - w) // 2
            y = (sh - h) // 2
            self.geometry(f'{w}x{h}+{x}+{y}')

        self.update_idletasks()
        self._win_w = self.winfo_width()
        self._win_h = self.winfo_height()

        # 缩放因子: 相对于 1280x720
        self._sx = self._win_w / _REF_W
        self._sy = self._win_h / _REF_H
        self._s = min(self._sx, self._sy)  # 统一缩放

        # 屏幕类型
        if self._win_w < 600:
            self._screen_type = 'phone'
        elif self._win_w < 1024:
            self._screen_type = 'tablet'
        else:
            self._screen_type = 'desktop'

    def s(self, size):
        """缩放尺寸 (字体/间距/按钮等)"""
        return max(8, int(size * self._s))

    def sx(self, size):
        """缩放水平尺寸"""
        return max(4, int(size * self._sx))

    def sy(self, size):
        """缩放垂直尺寸"""
        return max(4, int(size * self._sy))

    @property
    def screen_type(self):
        return self._screen_type

    @property
    def win_size(self):
        return self._win_w, self._win_h

    def _setup_fonts(self):
        base = self.s(14)
        self._default_font = tkfont.Font(family='Microsoft YaHei', size=base)
        self.option_add('*Font', self._default_font)

    def _build_ui(self):
        t = self._theme
        nav_h = self.sy(50)

        # --- 顶部导航栏 ---
        self.top_bar = tk.Frame(self, bg=t['bg_nav'], height=nav_h)
        self.top_bar.pack(fill='x')
        self.top_bar.pack_propagate(False)

        self.title_label = tk.Label(
            self.top_bar, text='学习助手',
            font=('Microsoft YaHei', self.s(20), 'bold'),
            bg=t['bg_nav'], fg=t['text'])
        self.title_label.pack(side='left', padx=self.sx(20))

        self.theme_btn = tk.Button(
            self.top_bar, text='深色模式',
            font=('Microsoft YaHei', self.s(12)),
            bg=t['accent_light'], fg=t['accent'], relief='flat', bd=0,
            command=self.toggle_theme)
        self.theme_btn.pack(side='right', padx=self.sx(20), pady=self.sy(8))

        tk.Frame(self, bg=t['border'], height=1).pack(fill='x')

        # --- 主内容区域 ---
        self.content = tk.Frame(self, bg=t['bg'])
        self.content.pack(fill='both', expand=True)

        tk.Frame(self, bg=t['border'], height=1).pack(fill='x')

        # --- 底部导航栏 ---
        self.bottom_nav = tk.Frame(self, bg=t['bg_nav'], height=nav_h)
        self.bottom_nav.pack(fill='x')
        self.bottom_nav.pack_propagate(False)

        tabs = [('flashcards', '卡片学习'), ('dictionary', '英文词典'),
                ('vocab', '生词本'), ('picturebook', '绘本打卡')]
        nav_font = ('Microsoft YaHei', self.s(14))
        self._nav_buttons = {}
        for key, label in tabs:
            btn = tk.Button(self.bottom_nav, text=label, font=nav_font,
                            bg=t['bg_nav'], fg=t['text_sec'], relief='flat', bd=0,
                            command=lambda k=key: self.show_tab(k))
            btn.pack(side='left', expand=True, fill='both')
            self._nav_buttons[key] = btn

    def _init_frames(self):
        self._frames = {}

        from studyapp.features.flashcards.screens import DeckListFrame, CardEditorFrame, StudyFrame
        from studyapp.features.dictionary.screens import DictionaryFrame, VocabListFrame
        from studyapp.features.picturebook.screens import PictureBookFrame

        self._frames['deck_list'] = DeckListFrame(self.content, self)
        self._frames['card_editor'] = CardEditorFrame(self.content, self)
        self._frames['study'] = StudyFrame(self.content, self)
        self._frames['dictionary'] = DictionaryFrame(self.content, self)
        self._frames['vocab_list'] = VocabListFrame(self.content, self)
        self._frames['picturebook'] = PictureBookFrame(self.content, self)

        for frame in self._frames.values():
            frame.grid(row=0, column=0, sticky='nsew')
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def show_tab(self, tab_key):
        self._active_tab = tab_key
        t = self._theme
        nav_font = ('Microsoft YaHei', self.s(14))

        for key, btn in self._nav_buttons.items():
            if key == tab_key:
                btn.configure(fg=t['accent'], font=(*nav_font[:2], nav_font[2], 'bold') if len(nav_font) > 2 else nav_font)
                btn.configure(font=('Microsoft YaHei', self.s(14), 'bold'))
            else:
                btn.configure(fg=t['text_sec'], font=('Microsoft YaHei', self.s(14)))

        frame_map = {
            'flashcards': 'deck_list',
            'dictionary': 'dictionary',
            'vocab': 'vocab_list',
            'picturebook': 'picturebook',
        }
        frame_key = frame_map.get(tab_key)
        if frame_key:
            self._show_frame(frame_key)

    def _show_frame(self, frame_key):
        frame = self._frames.get(frame_key)
        if frame:
            frame.tkraise()
            if hasattr(frame, 'on_enter'):
                frame.on_enter()

    def show_sub_screen(self, frame_key, **kwargs):
        frame = self._frames.get(frame_key)
        if frame and hasattr(frame, 'load'):
            frame.load(**kwargs)
        self._show_frame(frame_key)

    def toggle_theme(self):
        self._is_dark = not self._is_dark
        self._theme = DARK if self._is_dark else LIGHT
        self.theme_btn.configure(text='浅色模式' if self._is_dark else '深色模式')
        self._apply_theme()

    def _apply_theme(self):
        t = self._theme
        self.configure(bg=t['bg'])
        self.title_label.configure(bg=t['bg_nav'], fg=t['text'])
        self.theme_btn.configure(bg=t['accent_light'], fg=t['accent'])
        self.content.configure(bg=t['bg'])
        self.top_bar.configure(bg=t['bg_nav'])
        self.bottom_nav.configure(bg=t['bg_nav'])
        for key, btn in self._nav_buttons.items():
            bg = t['bg_nav']
            fg = t['accent'] if key == self._active_tab else t['text_sec']
            btn.configure(bg=bg, fg=fg)
        for frame in self._frames.values():
            if hasattr(frame, 'apply_theme'):
                frame.apply_theme()


if __name__ == '__main__':
    app = StudyApp()
    app.mainloop()
