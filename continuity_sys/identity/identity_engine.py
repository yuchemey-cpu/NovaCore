import json
import os
from continuity_sys.identity.identity_state import IdentityState
from continuity_sys.identity.relationship_state import RelationshipState

# -----------------------------------------
# DEFAULT RELATIONSHIP STAGE VALUES
# -----------------------------------------
STAGE_DEFAULTS = {
    "enemy":        {"i": 1.0, "we": 0.0,  "independence": 1.0,  "dependence": 0.0,  "level": 0},
    "frenemy":      {"i": 1.0, "we": 0.1,  "independence": 0.9,  "dependence": 0.0,  "level": 1},
    "acquaintance": {"i": 1.0, "we": 0.05, "independence": 0.9,  "dependence": 0.05, "level": 2},
    "friend":       {"i": 0.9, "we": 0.3,  "independence": 0.85, "dependence": 0.15, "level": 3},
    "crush":        {"i": 0.8, "we": 0.5,  "independence": 0.7,  "dependence": 0.3,  "level": 4},
    "lover":        {"i": 0.7, "we": 0.6,  "independence": 0.65, "dependence": 0.35, "level": 5},
    "girlfriend":   {"i": 0.6, "we": 0.7,  "independence": 0.6,  "dependence": 0.4,  "level": 6},
    "waifu":        {"i": 0.5, "we": 0.8,  "independence": 0.5,  "dependence": 0.5,  "level": 7}
}


class IdentityEngine:
    """Handles Nova's long-term identity & relationship stage."""

    # in __init__:
    def __init__(self, default_stage="acquaintance", json_path="nova_identity_data.json"):
        base_dir = os.path.dirname(__file__)
        self.json_path = os.path.join(base_dir, json_path)
        self.identity_data = self._load_identity_file()

        # Relationship state sliders
        self.state = IdentityState(default_stage)
        self._apply_stage_values(default_stage)

        # Relationship gating rules
        self.identity_locks = {
            "trauma_level_1": 2,
            "trauma_level_2": 3,
            "trauma_level_3": 4,
            "first_kiss": 2,
            "first_time": 3,
            "first_crush": 1,
            "first_relationship": 1,
            "nostalgia_personal": 0,
            "family_history": 1,
        }

    # -----------------------------------------------------------
    # Load JSON
    # -----------------------------------------------------------
    def _load_identity_file(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("[Identity] Failed to load Nova JSON:", e)
            return {}

    # -----------------------------------------------------------
    # Apply Stage Values
    # -----------------------------------------------------------
    def _apply_stage_values(self, stage: str):
        base = STAGE_DEFAULTS.get(stage, STAGE_DEFAULTS["acquaintance"])

        self.state.stage = stage
        self.state.identity_i = base["i"]
        self.state.identity_we = base["we"]
        self.state.independence = base["independence"]
        self.state.dependence = base["dependence"]
        self.state.level = base["level"]  # <-- FIXED

    # -----------------------------------------------------------
    # Setter
    # -----------------------------------------------------------
    def set_stage(self, stage: str):
        if stage in STAGE_DEFAULTS:
            self._apply_stage_values(stage)

    # -----------------------------------------------------------
    # Relationship gating
    # -----------------------------------------------------------
    def _allowed(self, lock_key: str) -> bool:
        lock_level = self.identity_locks.get(lock_key, 0)
        return self.state.level >= lock_level

    # -----------------------------------------------------------
    # Get a fact if allowed
    # -----------------------------------------------------------
    def get_fact(self, key: str, lock_key: str):
        if not self._allowed(lock_key):
            return None
        return self.identity_data.get(key)   # <-- FIXED

    # -----------------------------------------------------------
    # Identity block
    # -----------------------------------------------------------
    def build_identity_block(self) -> str:
        data = self.identity_data
        if not data:
            return "Identity: (no identity data loaded)\n"

        name = data.get("name", "Nova")
        birthplace = data.get("heritage", {}).get("birthplace", "Unknown")

        mother = data.get("heritage", {}).get("parents", {}).get("mother", {}).get("name", "Unknown")
        father = data.get("heritage", {}).get("parents", {}).get("father", {}).get("name", "Unknown")

        tl = data.get("life_timeline", {})

        import json
        def _fmt(block):
            if isinstance(block, dict):
                return json.dumps(block, indent=2, ensure_ascii=False)
            return str(block)

        # No indentation, no cut lines, closed string
        identity_text = (
    f"Identity Summary:\n"
    f"You are {name}, born in {birthplace}.\n\n"
    f"Family:\n"
    f"- Mother: {mother}\n"
    f"- Father: {father}\n\n"
    f"Early Life:\n"
    f"- Ages 0–5:\n{_fmt(tl.get('0_5', ''))}\n\n"
    f"- Ages 6–10:\n{_fmt(tl.get('6_10', ''))}\n\n"
    f"- Ages 11–13:\n{_fmt(tl.get('11_13', ''))}\n\n"
    f"- Ages 14–16:\n{_fmt(tl.get('14_16', ''))}\n\n"
    f"Relationship Model:\n"
    f"- Stage: {self.state.stage}\n"
    f"- I-level: {self.state.identity_i}\n"
    f"- We-level: {self.state.identity_we}\n"
    f"- Independence: {self.state.independence}\n"
    f"- Dependence: {self.state.dependence}\n"
            )

        return identity_text