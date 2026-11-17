"""Skill 注册表。最低交付 S1～S10 + polish。"""

from backend.app.skills.s1_topic import run_s1
from backend.app.skills.s2_retrieve import run_s2
from backend.app.skills.s3_parse import run_s3
from backend.app.skills.s4_compare import run_s4
from backend.app.skills.s5_classify import run_s5
from backend.app.skills.s6_gap import run_s6
from backend.app.skills.s7_outline import run_s7
from backend.app.skills.s8_write import run_s8
from backend.app.skills.s9_check import run_s9
from backend.app.skills.s10_export import run_s10
from backend.app.skills.polish import run_polish

SKILL_RUNNERS = {
    "S1": run_s1,
    "S2": run_s2,
    "S3": run_s3,
    "S4": run_s4,
    "S5": run_s5,
    "S6": run_s6,
    "S7": run_s7,
    "S8": run_s8,
    "S9": run_s9,
    "S10": run_s10,
    "polish": run_polish,
}

__all__ = [
    "SKILL_RUNNERS",
    "run_s1",
    "run_s2",
    "run_s3",
    "run_s4",
    "run_s5",
    "run_s6",
    "run_s7",
    "run_s8",
    "run_s9",
    "run_s10",
    "run_polish",
]
