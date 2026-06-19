from aiogram.fsm.context import FSMContext

from app.i18n import t

FLOW_STEPS = 5


def step_text(lang: str, step: int, key: str, **kwargs: str) -> str:
    body = t(lang, key, **kwargs)
    prefix = t(lang, "flow_step_prefix", step=str(step), total=str(FLOW_STEPS))
    return f"{prefix}\n\n{body}"


async def is_guided(state: FSMContext) -> bool:
    data = await state.get_data()
    return bool(data.get("guided_onboarding"))


async def flow_step(state: FSMContext) -> int | None:
    data = await state.get_data()
    step = data.get("flow_step")
    return int(step) if step else None


async def start_guided(state: FSMContext) -> None:
    await state.update_data(guided_onboarding=True, flow_step=1, first_digest_done=False)


async def set_flow_step(state: FSMContext, step: int) -> None:
    await state.update_data(flow_step=step)


async def mark_digest_done(state: FSMContext) -> None:
    await state.update_data(first_digest_done=True, flow_step=5)


async def finish_guided(state: FSMContext) -> None:
    await state.update_data(guided_onboarding=False, flow_step=None)
