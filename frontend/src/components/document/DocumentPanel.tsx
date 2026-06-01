import { Badge, Button, Group, Text, TextInput, Title } from "@mantine/core";
import {
  IconFile,
  IconMessageCircle,
  IconSend,
  IconUpload,
  IconAlertCircle,
} from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, type ChatResponse, type PlanDocument } from "../../api/client";
import styles from "./DocumentPanel.module.css";

type ChatMessage = {
  question: string;
  answer: string;
  sources: string[];
  grounded: boolean;
};

type Props = {
  planId: number;
  documents: PlanDocument[];
};

export default function DocumentPanel({ planId, documents }: Props) {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadDocument(planId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", planId] }),
  });

  const chat = useMutation({
    mutationFn: (q: string) => api.chatWithDocuments(planId, q),
    onSuccess: (data: ChatResponse, sentQuestion: string) => {
      setMessages((prev) => [
        ...prev,
        {
          question: sentQuestion,
          answer: data.answer,
          sources: data.sources,
          grounded: data.grounded,
        },
      ]);
      setQuestion("");
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
    e.target.value = "";
  }

  function handleSend() {
    if (!question.trim() || chat.isPending) return;
    chat.mutate(question.trim());
  }

  return (
    <div className={styles.panel}>
      {/* Header */}
      <Group justify="space-between" mb="lg">
        <Title order={4} className={styles.sectionTitle}>
          Documents
        </Title>
        <Group gap="sm">
          {documents.length > 0 && (
            <Badge color="violet" variant="light" size="sm">
              {documents.length} file{documents.length !== 1 ? "s" : ""}
            </Badge>
          )}
          <Button
            leftSection={<IconUpload size={13} />}
            color="violet"
            size="xs"
            variant="light"
            loading={upload.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            Upload PDF
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,text/plain"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
        </Group>
      </Group>

      {upload.isError && (
        <Text c="red" size="sm" mb="sm">
          {upload.error instanceof Error ? upload.error.message : "Upload failed."}
        </Text>
      )}

      {/* Document list */}
      {documents.length > 0 && (
        <div className={styles.docList}>
          {documents.map((doc) => (
            <div key={doc.id} className={styles.docItem}>
              <IconFile size={14} color="var(--c-turquoise)" style={{ flexShrink: 0 }} />
              <Text className={styles.docName}>{doc.filename}</Text>
              <Text className={styles.docMeta}>
                {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}
              </Text>
            </div>
          ))}
        </div>
      )}

      {/* Chat */}
      <div className={styles.chatSection}>
        <Group gap={6} mb="sm">
          <IconMessageCircle size={14} color="var(--c-cool-gray)" />
          <Text className={styles.chatLabel}>Ask about your documents</Text>
        </Group>

        {documents.length === 0 ? (
          <Text className={styles.emptyChat}>
            Upload a document to start asking questions.
          </Text>
        ) : (
          <>
            {messages.length > 0 && (
              <div className={styles.messageList}>
                {messages.map((msg, i) => (
                  <div key={i} className={styles.messageGroup}>
                    <div className={styles.question}>
                      <Text className={styles.questionText}>{msg.question}</Text>
                    </div>
                    <div className={styles.answer}>
                      <Text className={styles.answerText}>{msg.answer}</Text>
                      {!msg.grounded && (
                        <Group gap={4} mt={4}>
                          <IconAlertCircle size={12} color="var(--c-cool-gray)" />
                          <Text size="xs" c="dimmed">
                            No relevant content found in documents
                          </Text>
                        </Group>
                      )}
                      {msg.grounded && msg.sources.length > 0 && (
                        <Text size="xs" c="dimmed" mt={4}>
                          Source{msg.sources.length > 1 ? "s" : ""}:{" "}
                          {msg.sources.join(", ")}
                        </Text>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <Group gap="xs" mt="sm">
              <TextInput
                className={styles.questionInput}
                placeholder="Ask a question about your study materials…"
                value={question}
                onChange={(e) => setQuestion(e.currentTarget.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                disabled={chat.isPending}
              />
              <Button
                color="violet"
                size="sm"
                variant="light"
                loading={chat.isPending}
                onClick={handleSend}
                disabled={!question.trim()}
              >
                <IconSend size={14} />
              </Button>
            </Group>

            {chat.isError && (
              <Text c="red" size="xs" mt="xs">
                {chat.error instanceof Error ? chat.error.message : "Chat failed."}
              </Text>
            )}
          </>
        )}
      </div>
    </div>
  );
}
