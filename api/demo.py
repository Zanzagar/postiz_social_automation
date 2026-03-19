"""Demo mode: mock clients returning realistic Gita Valley sample data.

Enable with DEMO_MODE=true in .env. No Google Sheets, Postiz, or Claude needed.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from content_engine.models import ContentPillar, ContentRow, ContentStatus, Platform


class DemoSheetsClient:
    """Mock SheetsClient returning sample content."""

    def get_rows_by_status(self, status):
        return [r for r in self._rows() if r.status == status]

    def get_all_content_rows(self):
        return self._rows()

    def get_suggestions(self, status=None):
        return self._suggestions()

    def update_captions(self, row_number, captions):
        pass

    def update_status(self, row_number, status):
        pass

    def get_recent_errors(self, limit=10):
        return []

    def _rows(self):
        today = datetime.now()
        return [
            ContentRow(
                row_number=1,
                date=today + timedelta(days=1),
                content_pillar=ContentPillar.COW_LIFE,
                raw_text="Morning at the barn — Lakshmi and her calf enjoying the sunrise over the pasture. Our herd of 85 cows produces 400 gallons of ahimsa milk weekly.",
                media_url="https://drive.google.com/demo/lakshmi-sunrise.jpg",
                platforms={
                    Platform.INSTAGRAM: True,
                    Platform.FACEBOOK: True,
                    Platform.TIKTOK: False,
                },
                status=ContentStatus.PENDING_APPROVAL,
                captions={
                    Platform.INSTAGRAM: "Morning magic at Gita Valley! Lakshmi and her calf greet the sunrise.\n\nOur 85 cows roam freely on 430 acres of protected land. They're never separated from their calves and live their full natural lives.\n\n400 gallons of ahimsa milk every week — produced with love, not exploitation.\n\n#GitaValley #AhimsaMilk #CowProtection #FarmLife #SustainableLiving",
                    Platform.FACEBOOK: "Good morning from the barn!\n\nLakshmi and her calf are enjoying the first light over the pasture. At Gita Valley, our 85 cows roam freely across 430 acres and are never separated from their calves.\n\nEvery week they gift us 400 gallons of ahimsa milk — produced through love and care, never exploitation.\n\nWant to visit? Drop us a message!",
                },
                feedback=None,
                source="sheet",
            ),
            ContentRow(
                row_number=2,
                date=today + timedelta(days=2),
                content_pillar=ContentPillar.FARM_OPS,
                raw_text="Spring planting season begins! Our USDA-certified organic garden is expanding with new herb beds. Volunteers welcome every Saturday morning.",
                platforms={
                    Platform.INSTAGRAM: True,
                    Platform.FACEBOOK: True,
                    Platform.THREADS: True,
                },
                status=ContentStatus.PENDING_APPROVAL,
                captions={
                    Platform.INSTAGRAM: "Spring is here and we're getting our hands dirty!\n\nOur USDA-certified organic garden is expanding with new herb beds this season. Basil, tulsi, cilantro, and more.\n\nVolunteers welcome every Saturday 9am-12pm! No experience needed.\n\n#GitaValley #OrganicGarden #SpringPlanting #VolunteerLife #FarmToTable",
                    Platform.FACEBOOK: "Spring planting season is officially underway!\n\nOur USDA-certified organic garden is expanding with new herb beds — basil, tulsi, cilantro, and more. Everything we grow feeds our community kitchen.\n\nWant to help? Join our Saturday morning volunteer sessions (9am-12pm). No experience needed!",
                    Platform.THREADS: "Spring planting at Gita Valley. New herb beds going in this week. Volunteers welcome Saturdays 9am-12pm!",
                },
                feedback=None,
                source="sheet",
            ),
            ContentRow(
                row_number=3,
                date=today + timedelta(days=4),
                content_pillar=ContentPillar.KITCHEN,
                raw_text="This week's CSA box: fresh lettuce, spring onions, radishes, and our famous paneer made from ahimsa milk.",
                platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
                status=ContentStatus.PENDING_APPROVAL,
                captions={
                    Platform.INSTAGRAM: "This week's CSA box is packed with goodness!\n\nFresh lettuce, spring onions, radishes, and our famous paneer made from ahimsa milk!\n\nPlus a recipe card for paneer tikka with farm-fresh veggies.\n\nCSA memberships available — link in bio!\n\n#GitaValley #CSA #FarmFresh #AhimsaMilk #Paneer #FarmToTable",
                    Platform.FACEBOOK: "Your weekly CSA box is ready!\n\nThis week's harvest: fresh lettuce, spring onions, radishes, and our famous paneer (made from our own ahimsa milk!).\n\nNot a CSA member yet? Join today and get fresh, organic produce every week.",
                },
                feedback=None,
                source="sheet",
            ),
            ContentRow(
                row_number=4,
                date=today,
                content_pillar=ContentPillar.COMMUNITY,
                raw_text="Sunday Love Feast — every Sunday at 5pm. Free vegetarian meal, kirtan, and community gathering. All are welcome!",
                platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
                status=ContentStatus.SCHEDULED,
                captions={
                    Platform.INSTAGRAM: "Join us this Sunday for our weekly Love Feast!\n\n5:00 PM — Kirtan (devotional music)\n6:00 PM — Bhagavad Gita class\n6:30 PM — Free vegetarian feast\n\nAll are welcome. Bring your family, bring your friends.\n\n#GitaValley #SundayFeast #Kirtan #Vegetarian #Community",
                    Platform.FACEBOOK: "Join us this Sunday for our weekly Love Feast!\n\nGita Valley, Port Royal PA\n5:00 PM\n\nKirtan, Bhagavad Gita class, and a free vegetarian feast. All are welcome — families, friends, neighbors. No reservations needed.",
                },
                feedback=None,
                source="sheet",
            ),
            ContentRow(
                row_number=5,
                date=today - timedelta(days=2),
                content_pillar=ContentPillar.SPIRITUAL,
                raw_text="Bhagavad Gita verse of the week: 'Whatever you do, whatever you eat, whatever you offer or give away — do it as an offering to Me.' (9.27)",
                platforms={Platform.INSTAGRAM: True},
                status=ContentStatus.POSTED,
                captions={
                    Platform.INSTAGRAM: 'Verse of the Week\n\n"Whatever you do, whatever you eat, whatever you offer or give away — do it as an offering to Me."\n— Bhagavad Gita 9.27\n\nAt Gita Valley, every act of farming, cooking, and caring for our cows is done as an offering. The sacred isn\'t separate from the everyday.\n\n#GitaValley #BhagavadGita #SpiritualLife #DailyWisdom',
                },
                feedback=None,
                source="sheet",
            ),
            ContentRow(
                row_number=6,
                date=today - timedelta(days=5),
                content_pillar=ContentPillar.COW_LIFE,
                raw_text="Meet Dennis the ox! He's been at Gita Valley for 12 years and loves belly rubs.",
                platforms={Platform.INSTAGRAM: True, Platform.TIKTOK: True},
                status=ContentStatus.POSTED,
                captions={
                    Platform.INSTAGRAM: "Meet Dennis! Our gentle giant has been at Gita Valley for 12 years.\n\nDennis is one of our working oxen — he helps plow the fields the old-fashioned way. But his favorite activity? Belly rubs. Every. Single. Time.\n\nCome visit and meet Dennis and the rest of our 85-cow family!\n\n#GitaValley #Dennis #CowsOfInstagram #FarmAnimals #CowProtection",
                    Platform.TIKTOK: "Dennis the ox wants belly rubs and he wants them NOW. 12 years at Gita Valley and still the biggest baby on the farm #GitaValley #CowsOfTikTok #FarmLife",
                },
                feedback=None,
                source="sheet",
            ),
        ]

    def _suggestions(self):
        today = datetime.now()
        return [
            SimpleNamespace(
                suggested_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"),
                content_idea="Showcase the new greenhouse construction progress",
                suggested_pillar="Farm & Community",
                rationale="Community members have been asking about the greenhouse project. Visual progress updates drive 2x engagement.",
                media_suggestion="Photo of the greenhouse frame with volunteers working",
                status="pending",
            ),
            SimpleNamespace(
                suggested_date=(today + timedelta(days=5)).strftime("%Y-%m-%d"),
                content_idea="Behind the scenes: Morning milking routine with Lakshmi",
                suggested_pillar="Cow Life",
                rationale="Cow content consistently gets the highest engagement. Behind-the-scenes content performs 40% better than static posts.",
                media_suggestion="Short video clip of the morning milking process",
                status="pending",
            ),
            SimpleNamespace(
                suggested_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
                content_idea="Bhagavad Gita verse of the week with nature background",
                suggested_pillar="Spiritual Education",
                rationale="Weekly scripture posts have the highest save rate. Pairing with farm nature photos keeps it on-brand.",
                media_suggestion="Graphic with verse text overlay on sunrise-over-pasture photo",
                status="pending",
            ),
        ]


class DemoPostizClient:
    """Mock PostizClient returning demo integrations."""

    def list_integrations(self):
        return [
            {"id": "demo-ig", "identifier": "instagram", "name": "Gita Valley IG"},
            {"id": "demo-fb", "identifier": "facebook", "name": "Gita Valley FB"},
        ]

    def create_draft_post(self, content, platform_ids):
        return {"id": "demo-draft-001"}


class DemoCaptionGenerator:
    """Mock CaptionGenerator returning realistic brand-voice captions."""

    def generate_captions(self, row, feedback=None):
        captions = {}
        for platform, enabled in row.platforms.items():
            if not enabled:
                continue
            text = row.raw_text
            if platform == Platform.INSTAGRAM:
                captions[platform] = (
                    f"{text}\n\n"
                    "Visit us at Gita Valley — where soil and soul grow together.\n\n"
                    "#GitaValley #CultivatingSoilandSoul #FarmLife #SustainableLiving #AhimsaMilk"
                )
            elif platform == Platform.FACEBOOK:
                captions[platform] = (
                    f"{text}\n\n"
                    "At Gita Valley, we believe in living in harmony with nature. "
                    "Our 430-acre USDA-certified farm is home to 85 protected cows "
                    "and a thriving community.\n\n"
                    "Learn more or plan a visit — we'd love to welcome you!"
                )
            elif platform == Platform.TIKTOK:
                captions[platform] = f"{text} #GitaValley #FarmLife #CowsOfTikTok"
            elif platform == Platform.THREADS:
                captions[platform] = text
            elif platform == Platform.LINKEDIN:
                captions[platform] = (
                    f"{text}\n\n"
                    "Gita Valley is a 430-acre sustainable farming community in "
                    "Port Royal, PA integrating traditional agricultural practices "
                    "with modern organic certification."
                )
        if feedback:
            for p in captions:
                captions[p] = f"[Revised per feedback: {feedback}]\n\n{captions[p]}"
        return captions

    def iterate_single_caption(
        self,
        original_caption: str | None,
        platform: str,
        instruction: str,
        raw_text: str,
        pillar: str | None,
    ) -> str:
        """Demo iteration — simulates AI refinement by transforming the caption."""
        base = original_caption or raw_text
        lowered = instruction.lower()

        if "short" in lowered or "concise" in lowered:
            # Simulate shortening — take first sentence + instruction note
            first_sentence = base.split(".")[0].split("!")[0].split("\n")[0]
            return f"{first_sentence}. ✨\n\n#GitaValley"
        elif "emoji" in lowered:
            return f"🙏 {base} 🙏✨🌿"
        elif "formal" in lowered:
            return f"We are pleased to share: {base.replace('!', '.').replace('!!', '.')}"
        elif "question" in lowered:
            return f"Did you know? {base}\n\nWhat do you think? Let us know below! 👇"
        elif "hashtag" in lowered:
            return f"{base}\n\n#GitaValley #ISKCON #SpiritualLife #FarmLife #CowProtection #Bhagavadgita"
        elif "sentence" in lowered or "add" in lowered:
            return f"{base}\n\nJoin us at Gita Valley and experience the beauty of simple, spiritual living firsthand."
        else:
            # Generic refinement — rephrase slightly
            return f"{base}\n\n— Refined with love at Gita Valley 🙏"
