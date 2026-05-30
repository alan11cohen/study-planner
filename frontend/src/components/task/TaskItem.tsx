import { Checkbox, Group, Text } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import type { StudyTask } from "../../api/client";
import styles from "./TaskItem.module.css";

interface Props {
  task: StudyTask;
  onToggle: (taskId: number, completed: boolean) => void;
}

export default function TaskItem({ task, onToggle }: Props) {
  return (
    <div
      className={`${styles.taskItem} ${task.completed ? styles.taskCompleted : ""}`}
    >
      <Checkbox
        checked={task.completed}
        onChange={(e) => onToggle(task.id, e.currentTarget.checked)}
        color="cyan"
        size="sm"
      />
      <Text className={styles.taskTitle}>{task.title}</Text>
      <Group gap={4} className={styles.taskHours}>
        <IconClock size={12} color="var(--c-cool-gray)" />
        <Text className={styles.taskHoursText}>{task.estimated_hours}h</Text>
      </Group>
    </div>
  );
}
