import random
from datetime import datetime, timedelta
from .repository import get_due_cards, get_new_cards, get_card_progress, upsert_card_progress

# 级别对应的复习间隔(天)
INTERVAL_DAYS = {0: 0, 1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def get_study_cards(deck_id: int, daily_new_limit: int = 20):
    """获取本次学习的卡片: 到期卡片优先, 再补充新卡, 已掌握的不出现"""
    due = get_due_cards(deck_id)
    new = get_new_cards(deck_id)
    random.shuffle(due)
    random.shuffle(new)
    return due + new[:daily_new_limit]


def process_grade(card_id: int, grade: int) -> dict:
    """根据评分更新卡片进度, 返回新的进度记录"""
    progress = get_card_progress(card_id)
    current_level = progress['level'] if progress else 0

    # 计算新级别
    if grade == 0:       # 重来: 重置为0
        new_level = 0
    elif grade == 1:     # 困难: 原地不动
        new_level = current_level
    elif grade == 2:     # 良好: +1
        new_level = min(5, current_level + 1)
    else:                # 简单: +2
        new_level = min(5, current_level + 2)

    # 计算下次复习日期
    interval = INTERVAL_DAYS.get(new_level, 0)
    next_review = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d %H:%M:%S')

    upsert_card_progress(card_id, new_level, next_review)
    return {'card_id': card_id, 'level': new_level, 'next_review': next_review}


def grade_label(grade: int) -> str:
    return {0: "重来", 1: "困难", 2: "良好", 3: "简单"}.get(grade, "")
