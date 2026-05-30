import { Button, Loader, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus, IconTarget } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  api,
  getTokenPayload,
  type StudyPlan,
  type StudyTask,
} from "../../api/client";
import AppHeader from "../../components/layout/AppHeader";
import CreatePlanModal from "../../components/plan/CreatePlanModal";
import PlanCard from "../../components/plan/PlanCard";
import styles from "./Dashboard.module.css";

type PlanStats = { total: number; completed: number };

export default function Dashboard() {
  const navigate = useNavigate();
  const payload = getTokenPayload()!;
  const currentUserId = Number(payload.sub);

  const [newPlanOpened, { open: openNewPlan, close: closeNewPlan }] =
    useDisclosure(false);

  const { data: plans = [], isLoading: plansLoading } = useQuery<StudyPlan[]>({
    queryKey: ["plans", currentUserId],
    queryFn: () => api.getUserPlans(currentUserId),
  });

  const { data: taskStats = {} } = useQuery<Record<number, PlanStats>>({
    queryKey: ["taskStats", plans.map((p) => p.id)],
    queryFn: async () => {
      const entries = await Promise.all(
        plans.map(async (p) => {
          const tasks: StudyTask[] = await api.getTasks(p.id);
          return [
            p.id,
            {
              total: tasks.length,
              completed: tasks.filter((t) => t.completed).length,
            },
          ] as const;
        }),
      );
      return Object.fromEntries(entries);
    },
    enabled: plans.length > 0,
  });

  const totalTasks = Object.values(taskStats).reduce((s, x) => s + x.total, 0);
  const completedTasks = Object.values(taskStats).reduce(
    (s, x) => s + x.completed,
    0,
  );
  const remainingTasks = totalTasks - completedTasks;
  const totalHoursPerWeek = plans.reduce((s, p) => s + p.hours_per_week, 0);

  return (
    <div className={styles.page}>
      <AppHeader />

      <main className={styles.main}>
        <div className={styles.greeting}>
          <Title order={2} className={styles.greetingTitle}>
            Hi {payload.name}!
          </Title>
          {plans.length > 0 && (
            <div className={styles.stats}>
              <span className={styles.stat}>
                {plans.length} plan{plans.length !== 1 ? "s" : ""}
              </span>
              <span className={styles.statDot}>·</span>
              <span className={styles.stat}>
                {remainingTasks} task{remainingTasks !== 1 ? "s" : ""} remaining
              </span>
              <span className={styles.statDot}>·</span>
              <span className={styles.stat}>{totalHoursPerWeek}h / week</span>
            </div>
          )}
        </div>

        {plansLoading ? (
          <div className={styles.loader}>
            <Loader color="cyan" size="sm" />
          </div>
        ) : plans.length === 0 ? (
          <div className={styles.emptyPlans}>
            <IconTarget size={36} stroke={1.2} color="var(--c-cool-gray)" />
            <Text className={styles.emptyPlansText}>
              No plans yet — create one to get started.
            </Text>
            <Button
              leftSection={<IconPlus size={14} />}
              color="cyan"
              variant="light"
              size="sm"
              onClick={openNewPlan}
            >
              Create first plan
            </Button>
          </div>
        ) : (
          <div className={styles.grid}>
            {plans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                stats={taskStats[plan.id] ?? { total: 0, completed: 0 }}
                onClick={() => navigate(`/plans/${plan.id}`)}
              />
            ))}
            <button className={styles.addCard} onClick={openNewPlan}>
              <IconPlus size={22} color="var(--c-turquoise)" />
              <Text className={styles.addCardLabel}>New plan</Text>
            </button>
          </div>
        )}
      </main>

      <CreatePlanModal
        opened={newPlanOpened}
        onClose={closeNewPlan}
        userId={currentUserId}
      />
    </div>
  );
}
