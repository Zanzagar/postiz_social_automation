import { useEffect, useRef, useState, type ComponentType } from "react";
import { useQuery } from "@tanstack/react-query";
import { Network } from "lucide-react";

import { api } from "@/lib/api";
import { pillarColor } from "@/lib/pillars";
import { Chip, EmptyState, SkeletonText } from "@/components/pasture";
import { Button } from "@/components/ui/button";

// Documented brand hex values — canvas fills can't use CSS utility classes.
const TOPIC_COLOR = "#4a7c59"; // sage-500
const FALLBACK_NODE_COLOR = "#c4a484"; // terra-400

type GraphNode = Record<string, unknown>;

function isDarkMode(): boolean {
  return (
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark")
  );
}

function nodeColor(node: GraphNode): string {
  if (node.type === "topic") return TOPIC_COLOR;
  const site = node.site as string | undefined;
  return site ? pillarColor(site) : FALLBACK_NODE_COLOR;
}

/** Force-directed knowledge map — topics as hubs, pages orbiting them. */
export function GraphTab() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [ForceGraph, setForceGraph] = useState<ComponentType<
    Record<string, unknown>
  > | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "graph"],
    queryFn: () => api.getKnowledgeGraph(),
  });

  useEffect(() => {
    let active = true;
    void import("react-force-graph-2d").then((mod) => {
      if (active) setForceGraph(() => mod.default);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      setWidth(containerRef.current.clientWidth);
    }
  }, [ForceGraph, data]);

  const sites = Array.from(
    new Set(
      (data?.nodes ?? [])
        .map((n) => n.site)
        .filter((s): s is string => typeof s === "string" && s.length > 0),
    ),
  );

  if (isLoading || !ForceGraph) {
    return (
      <div className="px-4 py-5 sm:px-8">
        <div
          role="status"
          aria-label="Loading knowledge map"
          className="bg-card border-hair rounded-2xl p-6"
        >
          <SkeletonText lines={6} />
        </div>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <EmptyState
        icon={Network}
        title="Nothing to map yet"
        body="Once facts are extracted, topics and pages appear here as a living map."
      />
    );
  }

  const dark = isDarkMode();
  const topicLabelColor = dark ? "#d4ead9" : "#2d4a35"; // sage-100 / sage-700
  const pageLabelColor = dark ? "#a8d5b3" : "#737373"; // sage-200 / ink-muted

  return (
    <div className="px-4 py-5 sm:px-8">
      <div className="bg-card border-hair shadow-card overflow-hidden rounded-2xl">
        <div className="border-hair-b flex flex-wrap items-center justify-between gap-2 px-4 py-3">
          <div>
            <h3 className="t-body-sm font-semibold text-sage-800 dark:text-sage-100">
              Knowledge map
            </h3>
            <p className="t-caption ink-muted mt-0.5">
              Topics are hubs; pages orbit their dominant topic. Node size = fact count.
              Click to inspect.
            </p>
          </div>
          <div className="t-caption ink-muted flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ background: TOPIC_COLOR }}
                aria-hidden="true"
              />
              Topics
            </span>
            {sites.map((site) => (
              <span key={site} className="flex items-center gap-1.5">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: pillarColor(site) }}
                  aria-hidden="true"
                />
                {site} pages
              </span>
            ))}
          </div>
        </div>
        <div className="flex">
          <div
            ref={containerRef}
            role="img"
            aria-label="Knowledge map of topics and the pages they were extracted from"
            className="h-[500px] flex-1 overflow-hidden"
          >
            <ForceGraph
              graphData={data}
              nodeLabel={(node: GraphNode) => {
                const count = node.count as number | undefined;
                return `${String(node.label)}${count ? ` — ${count} facts` : ""}`;
              }}
              nodeColor={nodeColor}
              nodeVal={(node: GraphNode) => (node.size as number) ?? 3}
              nodeCanvasObject={(
                node: GraphNode,
                ctx: CanvasRenderingContext2D,
                globalScale: number,
              ) => {
                const x = node.x as number;
                const y = node.y as number;
                const size = (node.size as number) ?? 3;
                const isTopic = node.type === "topic";

                ctx.beginPath();
                ctx.arc(x, y, size, 0, 2 * Math.PI);
                ctx.fillStyle = nodeColor(node);
                ctx.fill();

                if (isTopic || globalScale > 1.5) {
                  const label = node.label as string;
                  const fontSize = isTopic ? 14 / globalScale : 10 / globalScale;
                  ctx.font = `${isTopic ? "600 " : ""}${fontSize}px Inter, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.fillStyle = isTopic ? topicLabelColor : pageLabelColor;
                  ctx.fillText(label, x, y + size + fontSize + 2);
                }
              }}
              linkColor={() =>
                dark ? "rgba(212, 234, 217, 0.12)" : "rgba(45, 74, 53, 0.12)"
              }
              linkWidth={0.5}
              width={selectedNode ? width - 260 : width}
              height={500}
              onNodeClick={(node: GraphNode) => setSelectedNode(node)}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          </div>

          {selectedNode && (
            <aside className="bg-warm w-[260px] shrink-0 border-l p-4">
              <div className="flex items-center justify-between gap-2">
                <Chip
                  tone={selectedNode.type === "topic" ? "sage" : "terra"}
                  className="capitalize"
                >
                  {String(selectedNode.type)}
                </Chip>
                <Button
                  size="xs"
                  variant="ghost"
                  className="fr"
                  onClick={() => setSelectedNode(null)}
                >
                  Close
                </Button>
              </div>
              <h4 className="t-title-sm ink mt-2 font-serif">
                {String(selectedNode.label)}
              </h4>
              {selectedNode.count ? (
                <p className="t-caption ink-muted mt-1">
                  {Number(selectedNode.count)} knowledge entries
                </p>
              ) : null}
              {selectedNode.site ? (
                <p className="t-caption ink-muted mt-1">
                  Source: {String(selectedNode.site)}
                </p>
              ) : null}
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
