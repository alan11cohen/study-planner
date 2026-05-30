import {
  Button,
  Group,
  Modal,
  NumberInput,
  Stack,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import styles from "./CreatePlanModal.module.css";

interface Props {
  opened: boolean;
  onClose: () => void;
  userId: number;
}

export default function CreatePlanModal({ opened, onClose, userId }: Props) {
  const qc = useQueryClient();
  const form = useForm({
    initialValues: {
      goal: "",
      description: "",
      hours_per_week: 10 as number | string,
      target_date: "",
    },
    validate: {
      goal: (v) => (v.trim() ? null : "Goal is required"),
    },
  });

  const createPlan = useMutation({
    mutationFn: () =>
      api.createPlan({
        user_id: userId,
        goal: form.values.goal,
        hours_per_week: Number(form.values.hours_per_week),
        description: form.values.description || null,
        target_date: form.values.target_date || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plans", userId] });
      handleClose();
    },
  });

  function handleClose() {
    onClose();
    form.reset();
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="New study plan"
      centered
      classNames={{ title: styles.modalTitle }}
    >
      <Stack gap="md">
        <TextInput
          label="Goal"
          placeholder="e.g. Pass AWS Solutions Architect exam"
          autoFocus
          {...form.getInputProps("goal")}
          onKeyDown={(e) =>
            e.key === "Enter" && form.values.goal.trim() && createPlan.mutate()
          }
        />
        <TextInput
          label="Description"
          placeholder="Optional notes or context"
          {...form.getInputProps("description")}
        />
        <NumberInput
          label="Hours per week"
          min={1}
          max={80}
          {...form.getInputProps("hours_per_week")}
        />
        <TextInput
          type="date"
          label="Target date (optional)"
          {...form.getInputProps("target_date")}
        />
        <Group justify="flex-end" mt="xs">
          <Button variant="subtle" color="gray" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            color="cyan"
            onClick={() => createPlan.mutate()}
            loading={createPlan.isPending}
            disabled={!form.values.goal.trim()}
          >
            Create plan
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
