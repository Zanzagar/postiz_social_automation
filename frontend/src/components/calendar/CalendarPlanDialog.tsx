import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CalendarPlanSlot } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CalendarPlus,
  Check,
  CheckCheck,
  Loader2,
  Sparkles,
} from "lucide-react";
import { format } from "date-fns";

const ALL_PLATFORMS = ["instagram", "facebook", "tiktok", "threads", "linkedin"];

type Phase = "configure" | "generating" | "review" | "done";

interface CalendarPlanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultStart: string;
  defaultEnd: string;
}

export function CalendarPlanDialog({
  open,
  onOpenChange,
  defaultStart,
  defaultEnd,
}: CalendarPlanDialogProps) {
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<Phase>("configure");

  // Configure state
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [platforms, setPlatforms] = useState<string[]>(["instagram", "facebook"]);
  const [constraints, setConstraints] = useState("");

  // Review state
  const [planId, setPlanId] = useState<number | null>(null);
  const [slots, setSlots] = useState<CalendarPlanSlot[]>([]);
  const [selectedSlots, setSelectedSlots] = useState<Set<number>>(new Set());
  const [approvedCount, setApprovedCount] = useState(0);

  const generateMutation = useMutation({
    mutationFn: () =>
      api.createCalendarPlan({
        date_range_start: startDate,
        date_range_end: endDate,
        platforms,
        constraints: constraints || undefined,
      }),
    onSuccess: (data) => {
      setPlanId(data.id);
      setSlots(data.slots);
      setSelectedSlots(new Set(data.slots.map((_, i) => i)));
      setPhase("review");
    },
    onError: () => {
      setPhase("configure");
    },
  });

  const approveMutation = useMutation({
    mutationFn: (indices: number[]) =>
      api.approveCalendarPlan(planId!, indices),
    onSuccess: (data) => {
      setApprovedCount(data.created_count);
      setPhase("done");
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  function handleGenerate() {
    setPhase("generating");
    generateMutation.mutate();
  }

  function toggleSlot(index: number) {
    setSelectedSlots((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function handleApprove(all: boolean) {
    const indices = all
      ? slots.map((_, i) => i)
      : Array.from(selectedSlots).sort();
    approveMutation.mutate(indices);
  }

  function handleClose() {
    setPhase("configure");
    setPlanId(null);
    setSlots([]);
    setSelectedSlots(new Set());
    setApprovedCount(0);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        {phase === "configure" && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CalendarPlus className="h-5 w-5" />
                Plan Content Calendar
              </DialogTitle>
              <DialogDescription>
                AI will generate a content calendar based on pillars, festivals,
                and your knowledge base.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label>Platforms</Label>
                <div className="flex flex-wrap gap-3 mt-2">
                  {ALL_PLATFORMS.map((p) => (
                    <label key={p} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={platforms.includes(p)}
                        onCheckedChange={(checked) => {
                          setPlatforms((prev) =>
                            checked
                              ? [...prev, p]
                              : prev.filter((x) => x !== p),
                          );
                        }}
                      />
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <Label>Constraints (optional)</Label>
                <Textarea
                  placeholder="e.g., Focus on farm content this week, avoid deity photos..."
                  value={constraints}
                  onChange={(e) => setConstraints(e.target.value)}
                  rows={2}
                />
              </div>

              {generateMutation.isError && (
                <p className="text-sm text-destructive">
                  Failed to generate plan. Please try again.
                </p>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={!startDate || !endDate || platforms.length === 0}
                className="gap-2"
              >
                <Sparkles className="h-4 w-4" />
                Generate Plan
              </Button>
            </DialogFooter>
          </>
        )}

        {phase === "generating" && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-sage-500 mb-4" />
            <p className="text-lg font-medium">Generating content plan...</p>
            <p className="text-sm text-muted-foreground mt-1">
              AI is analyzing pillars, festivals, and knowledge base
            </p>
          </div>
        )}

        {phase === "review" && (
          <>
            <DialogHeader>
              <DialogTitle>Review Plan ({slots.length} slots)</DialogTitle>
              <DialogDescription>
                {startDate} to {endDate} — select slots to approve
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-2 py-2 max-h-[50vh] overflow-y-auto">
              {slots.map((slot, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                    selectedSlots.has(i)
                      ? "bg-sage-50/50 border-sage-200"
                      : "opacity-50"
                  }`}
                >
                  <Checkbox
                    checked={selectedSlots.has(i)}
                    onCheckedChange={() => toggleSlot(i)}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{slot.date}</span>
                      {slot.time && (
                        <span className="text-xs text-muted-foreground">
                          {slot.time}
                        </span>
                      )}
                      {slot.pillar && (
                        <Badge variant="outline" className="text-xs">
                          {slot.pillar}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm mt-1">{slot.content_idea}</p>
                    {slot.target_platforms.length > 0 && (
                      <div className="flex gap-1 mt-1">
                        {slot.target_platforms.map((p) => (
                          <Badge
                            key={p}
                            variant="secondary"
                            className="text-[10px]"
                          >
                            {p}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                variant="outline"
                onClick={() => handleApprove(false)}
                disabled={
                  selectedSlots.size === 0 || approveMutation.isPending
                }
                className="gap-2"
              >
                <Check className="h-4 w-4" />
                Approve Selected ({selectedSlots.size})
              </Button>
              <Button
                onClick={() => handleApprove(true)}
                disabled={approveMutation.isPending}
                className="gap-2"
              >
                {approveMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCheck className="h-4 w-4" />
                )}
                Approve All
              </Button>
            </DialogFooter>
          </>
        )}

        {phase === "done" && (
          <>
            <div className="flex flex-col items-center justify-center py-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 mb-4">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <p className="text-lg font-medium">
                {approvedCount} drafts created
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                View them in Drafts or on the Calendar
              </p>
            </div>
            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
