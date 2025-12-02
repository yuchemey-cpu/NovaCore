class PersonalityCore:
    def __init__(self, traits=None):
        self.traits = traits or []

    def add_trait(self, trait):
        if trait not in self.traits:
            self.traits.append(trait)

    def remove_trait(self, trait):
        if trait in self.traits:
            self.traits.remove(trait)

    def get_traits(self):
        return list(self.traits)
