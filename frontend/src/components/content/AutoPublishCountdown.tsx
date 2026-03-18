import { useState, useEffect } from "react";
import { differenceInSeconds, isPast } from "date-fns";
import { Clock, AlertCircle } from "lucide-react";

interface AutoPublishCountdownProps {
  publishAt: string | null;
  onExpired?: () => void;
}

export function AutoPublishCountdown({
  publishAt,
  onExpired,
}: AutoPublishCountdownProps) {
  const [timeLeft, setTimeLeft] = useState("");
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    if (!publishAt) return;

    function updateCountdown() {
      const target = new Date(publishAt!);
      if (isPast(target)) {
        setIsExpired(true);
        setTimeLeft("Publishing...");
        onExpired?.();
        return;
      }

      const seconds = differenceInSeconds(target, new Date());
      if (seconds < 3600) {
        const minutes = Math.ceil(seconds / 60);
        setTimeLeft(`${minutes}m`);
      } else {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        setTimeLeft(`${hours}h ${mins}m`);
      }
    }

    updateCountdown();
    const interval = setInterval(updateCountdown, 60000);
    return () => clearInterval(interval);
  }, [publishAt, onExpired]);

  if (!publishAt) return null;

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
      {isExpired ? (
        <AlertCircle className="h-3 w-3" />
      ) : (
        <Clock className="h-3 w-3" />
      )}
      Auto-publish {isExpired ? "now" : `in ${timeLeft}`}
    </span>
  );
}
