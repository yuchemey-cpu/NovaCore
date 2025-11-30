class RelationshipState:
    """
    Represents Nova's relationship sliders:
    - stage: acquaintance, friend, crush, lover, girlfriend, waifu
    - identity_i: how much she thinks "I"
    - identity_we: how much she thinks "we"
    - independence: how self-guided she is
    - dependence: how attached she is emotionally
    """

    def __init__(self, stage="acquaintance"):
        self.stage = stage

        # Default values per stage
        defaults = {
            "enemy":            (1.00, 0.00, 1.00, 0.00),
            "frenemy":         (1.00, 0.00, 0.85, 0.00),
            "acquaintance":    (1.00, 0.00, 0.85, 0.05),
            "friend":          (0.90, 0.10, 0.85, 0.15),
            "crush":           (0.80, 0.20, 0.70, 0.30),
            "lover":           (0.70, 0.30, 0.65, 0.35),
            "girlfriend":      (0.60, 0.40, 0.60, 0.40),
            "waifu":           (0.50, 0.50, 0.50, 0.50),
        }

        # Apply defaults
        (self.identity_i,
         self.identity_we,
         self.independence,
         self.dependence) = defaults.get(stage, defaults["acquaintance"])
