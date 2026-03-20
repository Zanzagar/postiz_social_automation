import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export function PillarChart() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "pillars"],
    queryFn: () => api.getPillarBreakdown(),
  });

  const pillars = data?.pillars ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Engagement by Pillar</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-48 animate-pulse rounded bg-muted" />
        ) : pillars.length === 0 ? (
          <p className="text-sm text-muted-foreground">No analytics data yet</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pillars}>
              <XAxis dataKey="pillar" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="avg_engagement" fill="#4a7c59" radius={[4, 4, 0, 0]} name="Avg Engagement" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
