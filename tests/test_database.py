from src.database.models import Company
from src.database.repository import get_db_session, init_db
from src.recruitment.campaign_service import CampaignService


def test_database_initialization():
    init_db()
    with get_db_session() as session:
        companies = session.query(Company).all()
        assert len(companies) >= 1
        assert companies[0].name is not None


def test_create_campaign_and_job():
    with get_db_session() as session:
        campaign = CampaignService.create_campaign(
            session=session,
            company_name="Test Enterprise Inc",
            campaign_title="2026 AI Growth",
            target_hires=3,
        )
        assert campaign.id is not None
        assert campaign.title == "2026 AI Growth"

        job = CampaignService.create_job(
            session=session,
            campaign_id=campaign.id,
            title="Senior Test Engineer",
            description="Testing automated distributed microservices and reliability.",
            required_skills=["Python", "Pytest", "Docker"],
            min_years_experience=3.0,
            shortlist_threshold=70.0,
        )
        assert job.id is not None
        assert "Pytest" in job.required_skills
        assert job.shortlist_threshold == 70.0
