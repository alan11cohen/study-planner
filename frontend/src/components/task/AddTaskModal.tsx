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
import styles from "./AddTaskModal.module.css";

interface Props {
  opened: boolean;
  onClose: () => void;
  planId: number;
}

export default function AddTaskModal({ opened, onClose, planId }: Props) {
  const qc = useQueryClient();
  const form = useForm({
    initialValues: {
      title: "",
      estimated_hours: 2 as number | string,
    },
    validate: {
      title: (v) => (v.trim() ? null : "Title is required"),
    },
  });

  const addTask = useMutation({
    mutationFn: () =>
      api.createTask(planId, {
        title: form.values.title.trim(),
        estimated_hours: Number(form.values.estimated_hours),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", planId] });
      qc.invalidateQueries({ queryKey: ["taskStats"] });
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
      title="Add task"
      centered
      classNames={{ title: styles.modalTitle }}
    >
      <Stack gap="md">
        <TextInput
          label="Task title"
          placeholder="e.g. Read chapter 3 on EC2"
          autoFocus
          {...form.getInputProps("title")}
          onKeyDown={(e) =>
            e.key === "Enter" && form.values.title.trim() && addTask.mutate()
          }
        />
        <NumberInput
          label="Estimated hours"
          min={0.5}
          step={0.5}
          max={100}
          {...form.getInputProps("estimated_hours")}
        />
        <Group justify="flex-end" mt="xs">
          <Button variant="subtle" color="gray" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            color="cyan"
            onClick={() => addTask.mutate()}
            loading={addTask.isPending}
            disabled={!form.values.title.trim()}
          >
            Add task
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
