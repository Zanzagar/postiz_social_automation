/**
 * Simplified-but-faithful platform preview chrome (IG / FB / TikTok /
 * Threads / LinkedIn). These frames intentionally use fixed platform
 * colors (white cards, platform blues) — they replicate each network's
 * own UI and are not themable surfaces. Engagement counts are sample
 * numbers; the rail below the preview labels the whole thing approximate.
 */
import type * as React from "react";
import {
  Bookmark,
  Heart,
  MessageCircle,
  MoreHorizontal,
  Repeat2,
  Send,
  ThumbsUp,
} from "lucide-react";

export type IGVariant = "feed" | "reel" | "story";

interface PreviewProps {
  caption: string;
  image?: string | null;
  w?: number;
  variant?: IGVariant;
}

const SYS_FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
const PLACEHOLDER_BG = "linear-gradient(135deg, #d4ead9, #fff8e7 60%, #f2d0b0)";
const DARK_PLACEHOLDER = "radial-gradient(circle at 50% 30%, #7a5a3e, #2d4a35 60%, #000)";

function GVAvatar({ size = 32, ring = false }: { size?: number; ring?: boolean }) {
  return (
    <div
      className={
        ring
          ? "inline-flex shrink-0 rounded-full bg-gradient-to-tr from-[#feda75] via-[#fa7e1e] to-[#d62976] p-[2px]"
          : "inline-flex shrink-0 rounded-full"
      }
    >
      <div
        className="flex items-center justify-center rounded-full"
        style={{
          width: size,
          height: size,
          background: "linear-gradient(135deg, #2d4a35, #4a7c59 55%, #7cbf8d)",
        }}
        aria-hidden="true"
      >
        <span
          style={{
            color: "#fff8e7",
            fontWeight: 700,
            fontSize: Math.max(8, size * 0.38),
            letterSpacing: -0.5,
            fontFamily: "Georgia, serif",
          }}
        >
          GV
        </span>
      </div>
    </div>
  );
}

/** Caption text with platform-colored hashtags/mentions. */
function LinkedCaption({ caption, color }: { caption: string; color: string }) {
  const parts = caption.split(/(#[\wÀ-￿]+|@[\w.]+)/g);
  return (
    <span className="whitespace-pre-wrap">
      {parts.map((p, i) =>
        p.startsWith("#") || p.startsWith("@") ? (
          <span key={i} style={{ color }}>
            {p}
          </span>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </span>
  );
}

function Media({ image, ratio }: { image?: string | null; ratio: string }) {
  return (
    <div className="bg-neutral-100" style={{ aspectRatio: ratio }}>
      {image ? (
        <img src={image} alt="" className="h-full w-full object-cover" />
      ) : (
        <div className="h-full w-full" style={{ background: PLACEHOLDER_BG }} />
      )}
    </div>
  );
}

function VerticalFrame({
  image,
  w,
  children,
}: {
  image?: string | null;
  w: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="relative overflow-hidden rounded-[16px] shadow-lg"
      style={{ width: w, aspectRatio: "9/16", background: "#000", fontFamily: SYS_FONT }}
    >
      <div
        className="absolute inset-0"
        style={{
          background: image ? `url(${image}) center/cover` : DARK_PLACEHOLDER,
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,.4) 0, rgba(0,0,0,0) 18%, rgba(0,0,0,0) 55%, rgba(0,0,0,.8) 100%)",
        }}
      />
      {children}
    </div>
  );
}

function IGFeed({ caption, image, w = 320 }: PreviewProps) {
  return (
    <div
      className="flex flex-col overflow-hidden rounded-[14px] bg-white shadow-md"
      style={{ width: w, fontFamily: SYS_FONT, fontSize: 13, color: "#000" }}
    >
      <div className="flex items-center gap-2.5 px-3 py-2">
        <GVAvatar size={30} ring />
        <div className="min-w-0 flex-1 leading-tight">
          <div className="text-[13px] font-semibold">gitavalleyfarm</div>
          <div className="text-[11px] text-neutral-500">Port Royal, Pennsylvania</div>
        </div>
        <MoreHorizontal size={18} strokeWidth={1.75} aria-hidden="true" />
      </div>
      <Media image={image} ratio="4/5" />
      <div className="flex items-center px-3 pt-2.5 pb-1">
        <div className="flex items-center gap-3.5">
          <Heart size={22} strokeWidth={1.8} aria-hidden="true" />
          <MessageCircle size={22} strokeWidth={1.8} aria-hidden="true" />
          <Send size={22} strokeWidth={1.8} aria-hidden="true" />
        </div>
        <Bookmark size={22} strokeWidth={1.8} className="ml-auto" aria-hidden="true" />
      </div>
      <div className="px-3 text-[13px] leading-tight font-semibold">
        Liked by nandita.rao and 8,426 others
      </div>
      <div className="px-3 pt-1 pb-0.5 text-[13px] leading-snug">
        <span className="mr-1.5 font-semibold">gitavalleyfarm</span>
        <LinkedCaption caption={caption} color="#00376B" />
      </div>
      <div className="px-3 pt-1 text-[13px] leading-snug text-neutral-500">
        View all 184 comments
      </div>
      <div className="px-3 pt-1.5 pb-3 text-[10.5px] tracking-[0.04em] text-neutral-500 uppercase">
        2 hours ago
      </div>
    </div>
  );
}

function IGReel({ caption, image, w = 220 }: PreviewProps) {
  return (
    <VerticalFrame image={image} w={w}>
      <div className="absolute top-0 right-0 left-0 flex h-12 items-center px-3 text-white">
        <span className="text-[15px] font-semibold">Reels</span>
      </div>
      <div className="absolute right-2 bottom-14 flex flex-col items-center gap-4 text-white">
        <GVAvatar size={32} />
        <div className="flex flex-col items-center gap-0.5">
          <Heart size={24} strokeWidth={1.8} fill="#ED4956" stroke="#ED4956" aria-hidden="true" />
          <span className="text-[11px] font-semibold drop-shadow">12.4k</span>
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <MessageCircle size={24} strokeWidth={1.8} aria-hidden="true" />
          <span className="text-[11px] font-semibold drop-shadow">347</span>
        </div>
        <Send size={24} strokeWidth={1.8} aria-hidden="true" />
      </div>
      <div className="absolute right-12 bottom-3 left-0 px-3 text-white">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-[13px] font-semibold">gitavalleyfarm</span>
          <span className="rounded-md border border-white/80 px-2 py-0.5 text-[11px] font-semibold">
            Follow
          </span>
        </div>
        <div className="line-clamp-3 text-[12px] leading-snug drop-shadow">
          <LinkedCaption caption={caption} color="#9BD4FF" />
        </div>
      </div>
    </VerticalFrame>
  );
}

function IGStory({ caption, image, w = 220 }: PreviewProps) {
  return (
    <VerticalFrame image={image} w={w}>
      <div className="absolute top-2 right-2 left-2 flex gap-1">
        {[1, 0.5, 0, 0].map((p, i) => (
          <div key={i} className="h-[2px] flex-1 overflow-hidden rounded-full bg-white/30">
            <div className="h-full bg-white" style={{ width: `${p * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="absolute top-5 right-3 left-3 flex items-center gap-2 text-white">
        <GVAvatar size={26} />
        <span className="text-[13px] font-semibold">gitavalleyfarm</span>
        <span className="text-[11px] opacity-80">4h</span>
      </div>
      <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 text-center">
        <div
          className="inline-block max-w-[85%] rounded-md bg-white/95 px-3 py-2 text-[14px] leading-snug font-semibold text-neutral-900"
          style={{ fontFamily: "Georgia, serif" }}
        >
          {caption.split("\n")[0].slice(0, 80)}
        </div>
      </div>
      <div className="absolute right-3 bottom-3 left-3 flex items-center gap-2">
        <div className="flex h-9 flex-1 items-center rounded-full border border-white/50 px-4 text-[12.5px] text-white/80">
          Send message
        </div>
        <Heart size={20} strokeWidth={1.8} className="text-white" aria-hidden="true" />
      </div>
    </VerticalFrame>
  );
}

function FBPreview({ caption, image, w = 320 }: PreviewProps) {
  return (
    <div
      className="flex flex-col overflow-hidden rounded-[8px] bg-white shadow-md"
      style={{ width: w, fontFamily: SYS_FONT, color: "#050505" }}
    >
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <GVAvatar size={38} />
        <div className="min-w-0 flex-1 leading-tight">
          <div className="text-[14px] font-semibold">Gita Valley Farm</div>
          <div className="text-[12px]" style={{ color: "#65676B" }}>
            2h · 🌐
          </div>
        </div>
        <MoreHorizontal size={20} strokeWidth={1.75} style={{ color: "#65676B" }} aria-hidden="true" />
      </div>
      <div className="px-3 pb-2.5 text-[14px] leading-[1.33] whitespace-pre-wrap">
        <LinkedCaption caption={caption} color="#1877F2" />
      </div>
      {image && <Media image={image} ratio="5/4" />}
      <div
        className="flex items-center justify-between px-3 py-2 text-[13px]"
        style={{ color: "#65676B" }}
      >
        <span>👍❤️ Nandita Rao and 2,847 others</span>
        <span>186 comments</span>
      </div>
      <div
        className="grid grid-cols-3 border-t py-1 text-[13px] font-semibold"
        style={{ borderColor: "#CED0D4", color: "#65676B" }}
      >
        <span className="flex items-center justify-center gap-1.5 py-1.5">
          <ThumbsUp size={16} strokeWidth={1.75} aria-hidden="true" /> Like
        </span>
        <span className="flex items-center justify-center gap-1.5 py-1.5">
          <MessageCircle size={16} strokeWidth={1.75} aria-hidden="true" /> Comment
        </span>
        <span className="flex items-center justify-center gap-1.5 py-1.5">
          <Send size={16} strokeWidth={1.75} aria-hidden="true" /> Share
        </span>
      </div>
    </div>
  );
}

function TTPreview({ caption, image, w = 220 }: PreviewProps) {
  return (
    <VerticalFrame image={image} w={w}>
      <div className="absolute top-0 right-0 left-0 flex h-11 items-center justify-center gap-4 text-[14px] font-semibold text-white">
        <span className="opacity-70">Following</span>
        <span className="relative">
          For You
          <span className="absolute -bottom-1.5 left-1/2 h-[3px] w-4 -translate-x-1/2 rounded-full bg-white" />
        </span>
      </div>
      <div className="absolute right-2 bottom-16 flex flex-col items-center gap-4 text-white">
        <GVAvatar size={38} />
        <div className="flex flex-col items-center gap-0.5">
          <Heart size={28} strokeWidth={1.8} fill="#FE2C55" stroke="#FE2C55" aria-hidden="true" />
          <span className="text-[11px] font-semibold drop-shadow">124.3K</span>
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <MessageCircle size={28} strokeWidth={1.8} fill="#fff" stroke="#fff" aria-hidden="true" />
          <span className="text-[11px] font-semibold drop-shadow">3,218</span>
        </div>
      </div>
      <div className="absolute right-14 bottom-4 left-0 px-3 text-white">
        <div className="text-[14px] font-semibold">@gitavalleyfarm</div>
        <div className="mt-1 line-clamp-3 text-[12px] leading-snug drop-shadow">
          <LinkedCaption caption={caption} color="#25F4EE" />
        </div>
        <div className="mt-1.5 truncate text-[11px] opacity-95">
          ♫ original sound - gitavalleyfarm
        </div>
      </div>
    </VerticalFrame>
  );
}

function THPreview({ caption, image, w = 320 }: PreviewProps) {
  return (
    <div
      className="flex flex-col overflow-hidden rounded-[12px] bg-white shadow-md"
      style={{ width: w, fontFamily: SYS_FONT, color: "#000" }}
    >
      <div className="flex gap-3 px-4 py-3">
        <div className="flex flex-col items-center">
          <GVAvatar size={34} />
          <div className="mt-2 w-[2px] flex-1 rounded-full bg-neutral-200" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1">
            <span className="text-[14px] font-semibold">gitavalleyfarm</span>
            <span className="ml-1 text-[13px]" style={{ color: "#999" }}>
              2h
            </span>
            <MoreHorizontal
              size={16}
              strokeWidth={1.75}
              className="ml-auto"
              style={{ color: "#999" }}
              aria-hidden="true"
            />
          </div>
          <div className="mt-1 text-[14px] leading-[1.4] whitespace-pre-wrap">
            <LinkedCaption caption={caption} color="#0095F6" />
          </div>
          {image && (
            <div
              className="mt-3 overflow-hidden rounded-[14px] border border-neutral-200 bg-neutral-100"
              style={{ maxHeight: 220 }}
            >
              <img src={image} alt="" className="w-full object-cover" style={{ maxHeight: 220 }} />
            </div>
          )}
          <div className="mt-3 -ml-1 flex items-center gap-3">
            <Heart size={20} strokeWidth={1.8} aria-hidden="true" />
            <MessageCircle size={20} strokeWidth={1.8} aria-hidden="true" />
            <Repeat2 size={20} strokeWidth={1.8} aria-hidden="true" />
            <Send size={20} strokeWidth={1.8} aria-hidden="true" />
          </div>
          <div className="mt-1 text-[13px]" style={{ color: "#999" }}>
            487 replies · 3,241 likes
          </div>
        </div>
      </div>
    </div>
  );
}

function LIPreview({ caption, image, w = 320 }: PreviewProps) {
  return (
    <div
      className="flex flex-col overflow-hidden rounded-[8px] border bg-white shadow-md"
      style={{ width: w, fontFamily: SYS_FONT, color: "rgba(0,0,0,0.9)", borderColor: "#E9E5DF" }}
    >
      <div className="flex items-start gap-2 px-3 pt-3 pb-2">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-md"
          style={{ background: "linear-gradient(135deg, #2d4a35, #4a7c59)" }}
          aria-hidden="true"
        >
          <span
            className="text-[15px] font-bold text-white"
            style={{ fontFamily: "Georgia, serif", letterSpacing: -0.5 }}
          >
            GV
          </span>
        </div>
        <div className="min-w-0 flex-1 leading-tight">
          <div className="text-[14px] font-semibold">Gita Valley Farm</div>
          <div className="text-[12px]" style={{ color: "rgba(0,0,0,0.6)" }}>
            14,284 followers
          </div>
          <div className="text-[12px]" style={{ color: "rgba(0,0,0,0.6)" }}>
            2h · 🌐
          </div>
        </div>
        <span className="text-[13px] font-semibold" style={{ color: "#0A66C2" }}>
          + Follow
        </span>
      </div>
      <div className="px-3 pb-2 text-[13.5px] leading-[1.43] whitespace-pre-wrap">
        <LinkedCaption caption={caption} color="#0A66C2" />
      </div>
      {image && <Media image={image} ratio="1.91/1" />}
      <div
        className="flex items-center justify-between px-3 py-1.5 text-[12px]"
        style={{ color: "rgba(0,0,0,0.6)" }}
      >
        <span>👍💡 Nandita Rao and 486 others</span>
        <span>38 comments · 12 reposts</span>
      </div>
      <div
        className="grid grid-cols-4 border-t py-0.5 text-[12.5px] font-semibold"
        style={{ borderColor: "#E9E5DF", color: "rgba(0,0,0,0.6)" }}
      >
        {["Like", "Comment", "Repost", "Send"].map((l) => (
          <span key={l} className="flex items-center justify-center py-2">
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}

interface PlatformPreviewProps {
  platform: string;
  caption: string;
  image?: string | null;
  w?: number;
  variant?: IGVariant;
}

/** Unified entry point — representative chrome per platform. */
export function PlatformPreview({ platform, caption, image, w, variant }: PlatformPreviewProps) {
  switch (platform) {
    case "instagram":
      if (variant === "reel") return <IGReel caption={caption} image={image} w={w ?? 220} />;
      if (variant === "story") return <IGStory caption={caption} image={image} w={w ?? 220} />;
      return <IGFeed caption={caption} image={image} w={w ?? 320} />;
    case "facebook":
      return <FBPreview caption={caption} image={image} w={w ?? 320} />;
    case "tiktok":
      return <TTPreview caption={caption} image={image} w={w ?? 220} />;
    case "threads":
      return <THPreview caption={caption} image={image} w={w ?? 320} />;
    case "linkedin":
      return <LIPreview caption={caption} image={image} w={w ?? 320} />;
    default:
      return null;
  }
}
