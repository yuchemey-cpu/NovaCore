class IdentityState:
    """
    Holds Nova's long-term identity variables.
    Identity is NOT emotion — it's how she thinks of herself and her relationship.

    stage: relationship stage string
    identity_i: strength of "I" identity (0–1)
    identity_we: strength of "We" identity (0–1)
    independence: how self-contained she feels
    dependence: how emotionally invested she is
    """

    def __init__(self, stage: str = "acquaintance"):
        self.stage = stage

        # Default values for acquaintance
        self.identity_i = 1.0
        self.identity_we = 0.0
        self.independence = 0.90
        self.dependence = 0.05
