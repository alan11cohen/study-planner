import { Badge, Group, Progress, Text } from "@mantine/core";
import { IconCircleCheck, IconClock } from "@tabler/icons-react";
import type { StudyPlan } from "../../api/client";
import styles from "./PlanCard.module.css";

interface PlanStats {
  total: number;
  completed: number;
}

interface Props {
  plan: StudyPlan;
  stats: PlanStats;
  onClick: () => void;
}

function formatTargetDate(iso: string): { label: string; urgent: boolean } {
  const target = new Date(iso + "T00:00:00");
  const diffDays = Math.round(
    (target.getTime() - Date.now()) / (1000 * 60 * 60 * 24),
  );
  if (diffDays < 0) return { label: "Overdue", urgent: true };
  if (diffDays === 0) return { label: "Due today", urgent: true };
  if (diffDays <= 7) return { label: `${diffDays}d left`, urgent: true };
  return {
    label: target.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    urgent: false,
  };
}

export default function PlanCard({ plan, stats, onClick }: Props) {
  const isComplete = stats.total > 0 && stats.completed === stats.total;
  const progressPct =
    stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;
  const dateInfo =
    !isComplete && plan.target_date ? formatTargetDate(plan.target_date) : null;

  return (
    <button
      className={`${styles.card} ${isComplete ? styles.cardCompleted : ""}`}
      onClick={onClick}
    >
      <div className={styles.cardTop}>
        <Text className={styles.cardGoal}>{plan.goal}</Text>
        {isComplete ? (
          <Badge
            color="teal"
            variant="light"
            size="xs"
            leftSection={<IconCircleCheck size={11} />}
            className={styles.dateBadge}
          >
            Complete
          </Badge>
        ) : (
          dateInfo && (
            <Badge
              color={dateInfo.urgent ? "orange" : "gray"}
              variant="light"
              size="xs"
              className={styles.dateBadge}
            >
              {dateInfo.label}
            </Badge>
          )
        )}
      </div>

      {plan.description && (
        <Text className={styles.cardDescription}>{plan.description}</Text>
      )}

      <div className={styles.cardFooter}>
        <Group gap={6}>
          <IconClock size={12} color="var(--c-cool-gray)" />
          <Text className={styles.cardMetaText}>
            {plan.hours_per_week}h / week
          </Text>
        </Group>
        <Text className={styles.cardMetaText}>
          {stats.completed}/{stats.total} tasks
        </Text>
      </div>

      {stats.total > 0 && (
        <Progress
          value={progressPct}
          color={isComplete ? "teal" : "cyan"}
          size="xs"
          className={styles.progressBar}
        />
      )}
    </button>
  );
}
