from fastapi import APIRouter

from app.common.schemas import ERROR_RESPONSES
from app.core.deps import CurrentActor, ManagerActor, StaffActor, Uow
from app.core.errors import NotFoundError
from app.modules.organizations.models import BusinessCalendar, Holiday
from app.modules.organizations.repository import CalendarRepository, HolidayRepository, OrganizationRepository
from app.modules.organizations.schemas import CalendarIn, CalendarOut, HolidayIn, HolidayOut, OrganizationOut

router = APIRouter(prefix="/organization", tags=["organization"], responses=ERROR_RESPONSES)


@router.get("", response_model=OrganizationOut)
async def current_organization(actor: CurrentActor, uow: Uow) -> OrganizationOut:
    org = await OrganizationRepository(uow.session).by_id(actor.org_id)
    if org is None:
        raise NotFoundError()
    return OrganizationOut.model_validate(org)


@router.get("/calendar", response_model=CalendarOut)
async def get_calendar(actor: StaffActor, uow: Uow) -> CalendarOut:
    row = await CalendarRepository(uow.session, actor.org_id).settings()
    if row is None:
        raise NotFoundError()
    holidays = await HolidayRepository(uow.session, actor.org_id).list_all()
    return CalendarOut(
        timezone=row.timezone, weekly_hours=row.weekly_hours, holidays=[HolidayOut.model_validate(h) for h in holidays]
    )


@router.put("/calendar", response_model=CalendarOut)
async def update_calendar(body: CalendarIn, actor: ManagerActor, uow: Uow) -> CalendarOut:
    """New hours apply to tickets created or resumed from now on."""
    repo = CalendarRepository(uow.session, actor.org_id)
    row = await repo.settings() or repo.add(BusinessCalendar())
    row.timezone, row.weekly_hours = body.timezone, body.weekly_hours
    await uow.commit()
    return await get_calendar(actor, uow)


@router.post("/holidays", response_model=HolidayOut, status_code=201)
async def add_holiday(body: HolidayIn, actor: ManagerActor, uow: Uow) -> HolidayOut:
    holiday = HolidayRepository(uow.session, actor.org_id).add(Holiday(day=body.day, name=body.name))
    await uow.commit()
    return HolidayOut.model_validate(holiday)
