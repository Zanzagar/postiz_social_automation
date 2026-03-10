# Content Generation Strategy — Research

Date: 2026-02-24

## The Problem

Farm staff currently must manually specify everything for each post: text, platform,
timing, hashtags. This is labor-intensive and doesn't scale.

## Proposed Solution: Three-Layer Content Generation

### Layer 1: Raw Content Input (Staff Does This)

Minimal effort from farm staff — 1-3 sentences + optional photo/video:

```
"Lakshmi the cow enjoying morning sun. She just had her calf last week!"
+ photo from phone
+ select content pillar: "Cow Life"
+ check platforms: IG, FB, TT, TH
```

### Layer 2: AI Caption Generation (Automated)

Claude takes raw input and generates platform-optimized captions:

- **Instagram**: Visual storytelling, 20-30 hashtags, emoji-rich, call-to-action
- **Facebook**: Longer narrative, community engagement, minimal hashtags
- **TikTok**: Short punchy caption, trending hashtags, Gen-Z friendly tone
- **Threads**: Conversational, 500 char max, minimal hashtags
- **LinkedIn**: Professional tone, farm-as-business angle, 3-5 industry hashtags

Each caption is tailored to the platform's culture and constraints while maintaining
the Gita Valley brand voice.

### Layer 3: Content Pattern Extraction (Future Enhancement)

Analyze what works on similar accounts to improve content generation:

```
1. Scrape high-performing posts from similar accounts
   - Other ISKCON temples (e.g., @iskcontemples, @krishnaconsciousness)
   - Farm/homestead accounts (e.g., @polyface_farm)
   - Spiritual community accounts
    ↓
2. Classify patterns
   - What topics get high engagement?
   - What posting times work best?
   - What caption styles resonate?
   - What media types perform best?
    ↓
3. Feed patterns into AI prompts
   - "Posts about baby calves get 3x engagement"
   - "Behind-the-scenes kitchen content performs well on TikTok"
   - "Spiritual quotes with nature photos do best on Instagram"
    ↓
4. AI generates content informed by proven patterns
```

**Tools needed**: Apify (web scraping, ~$49/mo) or manual analysis
**n8n template reference**: [Viral Content Engine #9100](https://n8n.io/workflows/9100)

## Content Pillar Distribution (from Design Doc)

| Pillar | % | Examples | Best Platforms |
|--------|---|----------|---------------|
| Spiritual Education | 40% | Scripture quotes, arati, festivals, philosophy | IG, FB, Threads, LinkedIn |
| Farm & Community | 25% | Cow care, gardening, harvest, volunteer events | IG, FB, TikTok |
| Events | 15% | Sunday Feast, festivals, workshops | FB, IG, LinkedIn |
| Behind the Scenes | 10% | Kitchen prep, morning routines, seasons | TikTok, IG |
| Seasonal | 5% | Holidays, weather, planting/harvest cycles | All |
| Collaborative/CTA | 5% | Volunteer asks, donation drives, visit invitations | FB, LinkedIn |

## AI Prompt Architecture

### System Prompt Components

1. **Identity**: "You are the social media voice of Gita Valley (ISKCON Gita Nagari),
   a spiritual farming community in Pennsylvania."

2. **Brand voice**: Warm, authentic, spiritual but accessible. Not preachy.
   Use "we" language. Celebrate simple living and high thinking.

3. **Audience context**: Mix of devotees, curious seekers, farm/homestead enthusiasts,
   local community members, and spiritual-but-not-religious people.

4. **Platform rules**: Character limits, hashtag conventions, media requirements.

5. **Content pillar guidance**: Tone shifts by pillar (educational content is more
   reflective; farm content is more energetic; CTA content is direct).

6. **Negative constraints**: No controversial topics. No criticism of other traditions.
   No pressure to convert. No fundraising language unless explicitly a CTA post.

### Per-Platform Prompt Templates

Each platform gets a separate prompt that wraps the system prompt with
platform-specific instructions:

```
INSTAGRAM:
- Start with an attention-grabbing first line (shows in feed preview)
- Use line breaks for readability
- Include 20-30 relevant hashtags in a separate block
- End with a call-to-action (visit, comment, share)
- Emoji use: moderate, authentic

FACEBOOK:
- Can be longer (200-500 words for best engagement)
- Tell a story or share context
- Ask a question to drive comments
- 0-3 hashtags only
- Tag location: Gita Valley, Port Royal, PA

TIKTOK:
- Under 150 characters for caption overlay
- Trending hashtags (research current trends)
- Conversational, energetic tone
- Hook in first 3 words

THREADS:
- Under 500 characters
- Conversational, like texting a friend
- No hashtags (or 1-2 max)
- Can be part of a thread for longer stories

LINKEDIN:
- Professional/educational angle
- Farm-as-sustainable-business framing
- Tag relevant organizations
- 3-5 industry hashtags (#SustainableFarming, #CommunityLiving, etc.)
```

## What Staff Needs to Provide (Minimum)

| Field | Required? | Example |
|-------|-----------|---------|
| Raw text | Yes (1-3 sentences) | "Lakshmi had her calf this morning!" |
| Content pillar | Yes (dropdown) | Cow Life |
| Photo/video | Recommended | Phone photo of Lakshmi + calf |
| Target platforms | Yes (checkboxes) | IG, FB, TT, TH |
| Desired post date | Yes | 2026-03-01 |

Everything else (captions, hashtags, formatting, optimal time) is generated by AI.

## Implementation Phases

### Phase 1: Basic AI Captions (MVP)
- Staff provides raw text + media + platforms
- Claude generates one caption per platform
- Human reviews and approves
- Postiz publishes

### Phase 2: Smart Content Enhancement
- AI suggests optimal posting times per platform
- Auto-generate hashtags based on content + trending topics
- Media optimization (crop suggestions, alt text generation)

### Phase 3: Content Pattern Learning
- Analyze engagement data from Postiz analytics
- Track which content pillars perform best on which platforms
- AI adapts caption style based on what works

### Phase 4: Semi-Autonomous Content (Stretch)
- AI suggests content ideas based on calendar events (festivals, seasons)
- Auto-generate posts from Temple calendar
- Content recycling: resurface high-performing posts after 90 days
