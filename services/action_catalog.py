from models.action_spec import ActionSpec


class ActionCatalog:
    """
    Unified catalog of executable tools and capabilities.

    The catalog discovers executable actions from the registered
    ToolRegistry and CapabilityRegistry.

    Action metadata is owned by the executable itself through
    its ActionSpec. The catalog does not contain prompt-specific
    or capability-specific business logic.
    """

    def __init__(
        self,
        tool_registry,
        capability_registry,
    ) -> None:
        self.tool_registry = tool_registry
        self.capability_registry = capability_registry

    def specs(self) -> list[ActionSpec]:
        specs: list[ActionSpec] = []
        seen: set[str] = set()

        specs.extend(
            self._collect_specs(
                registry=self.capability_registry,
                kind="capability",
                seen=seen,
            )
        )

        specs.extend(
            self._collect_specs(
                registry=self.tool_registry,
                kind="tool",
                seen=seen,
            )
        )

        return specs

    def names(self) -> list[str]:
        return [
            spec.name
            for spec in self.specs()
        ]

    def as_prompt_context(self) -> list[dict]:
        return [
            spec.to_dict()
            for spec in self.specs()
        ]

    @staticmethod
    def _collect_specs(
        registry,
        kind,
        seen: set[str],
    ) -> list[ActionSpec]:

        specs: list[ActionSpec] = []

        for name in registry.get_registered_names():

            if name in seen:
                raise ValueError(
                    f"Executable action '{name}' is registered "
                    "more than once."
                )

            executable = registry.get(name)

            spec = ActionCatalog._resolve_spec(
                executable=executable,
                name=name,
                kind=kind,
            )

            specs.append(spec)
            seen.add(name)

        return specs

    @staticmethod
    def _resolve_spec(
        executable,
        name: str,
        kind,
    ) -> ActionSpec:

        spec = getattr(
            executable,
            "action_spec",
            None,
        )

        if spec is not None:

            if not isinstance(
                spec,
                ActionSpec,
            ):
                raise TypeError(
                    f"Executable '{name}' exposes "
                    "'action_spec', but it is not an "
                    "ActionSpec instance."
                )

            if spec.name != name:
                raise ValueError(
                    f"ActionSpec name '{spec.name}' does not "
                    f"match registered executable '{name}'."
                )

            if spec.kind != kind:
                raise ValueError(
                    f"ActionSpec kind '{spec.kind}' does not "
                    f"match registry kind '{kind}' for "
                    f"'{name}'."
                )

            return spec

        return ActionSpec(
            name=name,
            kind=kind,
            description=(
                f"Executable {kind}: {name}."
            ),
        )