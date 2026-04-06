<template>
  <div v-if="instance" class="flex flex-col h-full bg-warm-50 dark:bg-warm-900">
    <!-- Header -->
    <div class="flex items-center gap-3 px-4 py-2 border-b border-warm-200 dark:border-warm-700 bg-white dark:bg-warm-800">
      <StatusDot :status="instance.status" />
      <span class="font-medium text-warm-700 dark:text-warm-300">{{
        instance.config_name
      }}</span>
      <span class="text-xs text-warm-400">Editor</span>

      <!-- Open file tabs -->
      <div class="flex items-center gap-0.5 ml-2 overflow-x-auto">
        <div
          v-for="filePath in editor.openFilePaths"
          :key="filePath"
          class="flex items-center gap-1 px-2 py-1 rounded text-[11px] cursor-pointer select-none transition-colors max-w-40"
          :class="editor.activeFilePath === filePath
            ? 'bg-iolite/10 dark:bg-iolite/15 text-iolite dark:text-iolite-light'
            : 'text-warm-400 hover:text-warm-600 dark:hover:text-warm-300 hover:bg-warm-100 dark:hover:bg-warm-700'"
          @click="editor.activeFilePath = filePath"
        >
          <span
            v-if="editor.openFiles[filePath]?.dirty"
            class="w-1.5 h-1.5 rounded-full bg-amber shrink-0"
          />
          <span class="truncate">{{ fileName(filePath) }}</span>
          <button
            class="ml-0.5 w-3.5 h-3.5 flex items-center justify-center rounded-sm text-warm-400 hover:text-warm-600 dark:hover:text-warm-300"
            @click.stop="editor.closeFile(filePath)"
          >
            <div class="i-carbon-close text-[9px]" />
          </button>
        </div>
      </div>

      <div class="flex-1" />
      <button
        class="nav-item !w-7 !h-7 text-warm-500 hover:!text-warm-700 dark:hover:!text-warm-300"
        title="Back to instance"
        @click="$router.push(`/instances/${$route.params.id}`)"
      >
        <div class="i-carbon-close text-sm" />
      </button>
    </div>

    <!-- Main layout -->
    <div class="flex-1 overflow-hidden">
      <SplitPane
        :initial-size="20"
        :min-size="12"
        persist-key="editor-tree"
      >
        <template #first>
          <FileTree
            ref="fileTreeRef"
            :root="treeRoot"
            @select="onFileSelect"
          />
        </template>
        <template #second>
          <SplitPane
            :initial-size="60"
            :min-size="30"
            persist-key="editor-main"
          >
            <template #first>
              <div class="h-full flex flex-col">
                <MonacoEditor
                  v-if="editor.activeFile"
                  :file-path="editor.activeFilePath"
                  :content="editor.activeFile.content"
                  :language="editor.activeFile.language"
                  @change="onEditorChange"
                  @save="onEditorSave"
                />
                <div
                  v-else
                  class="h-full flex items-center justify-center text-warm-400 text-sm"
                >
                  <div class="text-center">
                    <div class="i-carbon-document text-3xl mb-2 mx-auto opacity-30" />
                    <p>Select a file to edit</p>
                  </div>
                </div>
              </div>
            </template>
            <template #second>
              <SplitPane
                horizontal
                :initial-size="70"
                :min-size="20"
                persist-key="editor-right"
              >
                <template #first>
                  <ChatPanel :instance="instance" />
                </template>
                <template #second>
                  <EditorStatus :instance="instance" />
                </template>
              </SplitPane>
            </template>
          </SplitPane>
        </template>
      </SplitPane>
    </div>
  </div>
</template>

<script setup>
import StatusDot from "@/components/common/StatusDot.vue";
import SplitPane from "@/components/common/SplitPane.vue";
import ChatPanel from "@/components/chat/ChatPanel.vue";
import FileTree from "@/components/editor/FileTree.vue";
import MonacoEditor from "@/components/editor/MonacoEditor.vue";
import EditorStatus from "@/components/editor/EditorStatus.vue";
import { useInstancesStore } from "@/stores/instances";
import { useChatStore } from "@/stores/chat";
import { useEditorStore } from "@/stores/editor";

const route = useRoute();
const instances = useInstancesStore();
const chat = useChatStore();
const editor = useEditorStore();

const fileTreeRef = ref(null);
const instance = computed(() => instances.current);
const treeRoot = computed(() => instance.value?.pwd || "");

onMounted(() => {
  loadInstance();
});

watch(() => route.params.id, loadInstance);

async function loadInstance() {
  const id = route.params.id;
  if (!id) return;
  await instances.fetchOne(id);
  if (instance.value) {
    chat.initForInstance(instance.value);
  }
}

function fileName(path) {
  return path.split("/").pop() || path.split("\\").pop() || path;
}

function onFileSelect(path) {
  editor.openFile(path);
}

function onEditorChange(content) {
  if (editor.activeFilePath) {
    editor.updateContent(editor.activeFilePath, content);
  }
}

function onEditorSave() {
  if (editor.activeFilePath) {
    editor.saveFile(editor.activeFilePath);
  }
}

// Watch for tool_done events that involve file writes -> refresh tree + reload file
watch(
  () => chat.currentMessages,
  (msgs) => {
    if (!msgs.length) return;
    const last = msgs[msgs.length - 1];
    if (!last.tool_calls) return;
    for (const tc of last.tool_calls) {
      if (tc.status === "done" && (tc.name === "write" || tc.name === "edit" || tc.name === "bash")) {
        fileTreeRef.value?.refresh();
        // Reload the active file if it might have been modified
        if (editor.activeFilePath) {
          editor.revertFile(editor.activeFilePath);
        }
        break;
      }
    }
  },
  { deep: true },
);
</script>
