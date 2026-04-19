import importlib

class AlgorithmPlugin:
    def __init__(self, config):
        self.config = config

        alg_conf = self.config.get('algorithm', {})

        # Default fallbacks
        sched_name = alg_conf.get('scheduler', 'round_robin')
        route_name = alg_conf.get('routing', 'best_relay')
        mob_name = alg_conf.get('mobility', 'static_positions')

        self.scheduler = self._load_module('algorithms.schedulers', sched_name)
        self.router = self._load_module('algorithms.routing', route_name)
        self.mobility_controller = self._load_module('algorithms.mobility', mob_name)

    def _load_module(self, base_path, module_name):
        full_module_name = f"{base_path}.{module_name}"
        module = importlib.import_module(full_module_name)

        # Find the class inside the module that inherits from BaseAlgorithm interfaces
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr.__module__ == full_module_name:
                # instantiate it
                return attr()

        raise ImportError(f"Could not find valid algorithm class in {full_module_name}")

    def observe(self, state):
        self.scheduler.observe(state)
        self.router.observe(state)
        self.mobility_controller.observe(state)

    def decide(self):
        # We don't strictly use a monolithic decide anymore, the apply takes care of it
        pass

    def apply(self, environment):
        self.scheduler.apply(environment)
        self.router.apply(environment)
        self.mobility_controller.apply(environment)

    def get_active_user(self, uav, all_users):
        """Pass-through hook for the micro-step scheduling."""
        if hasattr(self.scheduler, 'get_active_user'):
            # Some schedulers need all_users, some don't. We inspect to be safe.
            import inspect
            sig = inspect.signature(self.scheduler.get_active_user)
            if len(sig.parameters) == 2:
                return self.scheduler.get_active_user(uav, all_users)
            return self.scheduler.get_active_user(uav)
        else:
            # Fallback random
            import numpy as np
            return np.random.choice(uav.assigned_users) if uav.assigned_users else None

    def get_movements(self):
        """Pass-through hook for mobility."""
        decision = self.mobility_controller.decide()
        return decision.get('movements', {})
