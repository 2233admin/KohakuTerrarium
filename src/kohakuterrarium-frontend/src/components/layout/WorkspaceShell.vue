<template>
  <div class="workspace-shell h-full w-full flex flex-col overflow-hidden">
    <!-- Optional header passthrough — pages can inject their own title bar -->
    <div v-if="$slots.header" class="workspace-shell__header shrink-0">
      <slot name="header" />
    </div>

    <!-- Edit-mode banner (appears only when layout.editMode is true) -->
    <EditModeBanner />

    <!-- Preset strip: hidden when using a legacy preset so the old routes
         stay pixel-identical to pre-refactor. -->
    <PresetStrip v-if="showPresetStrip" class="shrink-0" />

    <!-- Save-as-new-preset modal — opened by the strip's "+" or the
         edit-mode banner's "Save as new" button via layoutEvents. -->
    <SavePresetModal v-model="saveModalOpen" @saved="onSaved" />

    <!-- Main body: horizontal zones (Splitpanes) + optional drawer + status bar -->
    <div class="workspace-shell__body flex-1 min-h-0 flex flex-col">
      <!-- Top section: horizontal zone strip -->
      <div class="workspace-shell__top flex-1 min-h-0 overflow-hidden">
        <Splitpanes
          v-if="horizontalPanes.length > 0"
          class="workspace-shell__zones"
          :dbl-click-splitter="false"
          @resize="onHorizontalResize"
        >
          <Pane
            v-for="(z, idx) in horizontalPanes"
            :key="z.zoneId + ':' + idx"
            :size="z.size"
            :min-size="z.minSize ?? 5"
          >
            <component
              :is="zoneComponentFor(z.type)"
              :zone-id="z.zoneId"
              :instance-id="instanceId"
              :show-empty="showEmpty"
            />
          </Pane>
        </Splitpanes>
        <div v-else class="h-full w-full" />
      </div>

      <!-- Drawer (optional) -->
      <ZoneDrawer
        v-if="drawerVisible"
        :zone-id="'drawer'"
        :instance-id="instanceId"
        :show-empty="showEmpty"
        :style="{ height: drawerHeight + 'px' }"
        class="shrink-0"
      />

      <!-- Status bar (optional strip) -->
      <ZoneStrip
        v-if="statusBarVisible"
        :zone-id="'status-bar'"
        :instance-id="instanceId"
        :show-empty="showEmpty"
        class="shrink-0"
      />
    </div>

    <!-- Singleton ChatPanel — mounted exactly once at the shell root
         and teleported into whichever zone slot currently hosts the
         `chat` panel. Mounted detached (off-screen) when no slot hosts
         chat so component-local UI state and keybind listeners survive
         a switch to a no-chat preset. -->
    <Teleport
      :to="chatMountSelector"
      :disabled="!chatSlotActive"
      :defer="true"
    >
      <div
        class="h-full w-full"
        :style="chatSlotActive ? undefined : offscreenStyle"
      >
        <ChatPanel v-bind="chatPanelProps" />
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { Pane, Splitpanes } from "splitpanes";
import "splitpanes/dist/splitpanes.css";

import { computed, inject, onMounted, onUnmounted, ref } from "vue";

import ChatPanel from "@/components/chat/ChatPanel.vue";
import PresetStrip from "@/components/chrome/PresetStrip.vue";
import { useLayoutStore } from "@/stores/layout";
import { LAYOUT_EVENTS, onLayoutEvent } from "@/utils/layoutEvents";
import EditModeBanner from "./EditModeBanner.vue";
import SavePresetModal from "./SavePresetModal.vue";
import ZoneAux from "./ZoneAux.vue";
import ZoneDrawer from "./ZoneDrawer.vue";
import ZoneMain from "./ZoneMain.vue";
import ZoneSidebar from "./ZoneSidebar.vue";
import ZoneStrip from "./ZoneStrip.vue";

// Mount the singleton off-screen when no slot hosts chat.
const offscreenStyle = {
  position: "absolute",
  left: "-99999px",
  width: "1px",
  height: "1px",
  overflow: "hidden",
  pointerEvents: "none",
};

const props = defineProps({
  instanceId: { type: String, default: null },
  /** Enable edit mode placeholders (Phase 5). */
  showEmpty: { type: Boolean, default: false },
  /** Fixed drawer height in px. Drag handle lands in Phase 5. */
  drawerHeight: { type: Number, default: 160 },
  /** When true, the preset switcher strip is shown at the top. */
  presetStrip: { type: Boolean, default: true },
});

const layout = useLayoutStore();

// ─── Narrow-window fallback ───────────────────────────────────
// Below 900 px the shell auto-collapses side zones to keep just the
// main zone + status bar usable. The user can still open other
// panels via the command palette or the preset strip.
const windowWidth = ref(
  typeof window !== "undefined" ? window.innerWidth : 1600,
);
function onResize() {
  if (typeof window !== "undefined") windowWidth.value = window.innerWidth;
}
const isNarrow = computed(() => windowWidth.value < 900);

// Runtime panel props injected by the route. We read `chat` from the
// map for the singleton ChatPanel so page owners can still pass e.g.
// the current instance without going through the store.
const panelPropsSource = inject("panelProps", () => ({}), true);

const chatPanelProps = computed(() => {
  const src =
    typeof panelPropsSource === "function" ? panelPropsSource() : panelPropsSource;
  // `src` may itself be a ref-like (pinia computed), so unwrap `.value`.
  const unwrapped = src && typeof src === "object" && "value" in src ? src.value : src;
  return unwrapped?.chat || {};
});

// Canonical horizontal zone order, left to right.
const HORIZONTAL_ORDER = [
  { zoneId: "left-sidebar", type: "sidebar" },
  { zoneId: "left-aux", type: "aux" },
  { zoneId: "main", type: "main" },
  { zoneId: "right-aux", type: "aux" },
  { zoneId: "right-sidebar", type: "sidebar" },
];

const preset = computed(() => layout.effectivePreset(props.instanceId));

const showPresetStrip = computed(() => {
  if (!props.presetStrip) return false;
  const id = layout.activePresetId || "";
  // Legacy presets keep the old pixel-identical look.
  return !id.startsWith("legacy-");
});

/**
 * Filter horizontal zones to those that are (a) visible in the preset AND
 * (b) have at least one slot assigned. Each entry carries its size ratio.
 */
const horizontalPanes = computed(() => {
  const p = preset.value;
  if (!p) return [];
  const out = [];
  for (const { zoneId, type } of HORIZONTAL_ORDER) {
    const z = p.zones?.[zoneId];
    if (!z || z.visible === false) continue;
    // Narrow window: hide sidebars + aux zones, keep main only. The
    // main zone may still host chat or whichever panel the preset
    // picked for it.
    if (isNarrow.value && zoneId !== "main") continue;
    const slots = p.slots?.filter((s) => s.zoneId === zoneId) || [];
    if (slots.length === 0 && !props.showEmpty) continue;
    out.push({
      zoneId,
      type,
      size: typeof z.size === "number" ? z.size : null,
      minSize: z.minSize,
    });
  }
  // Normalize sizes: if any are null/missing, distribute remainder equally.
  const assignedTotal = out.reduce((acc, z) => acc + (z.size || 0), 0);
  const missing = out.filter((z) => z.size == null);
  if (missing.length > 0) {
    const remainder = Math.max(0, 100 - assignedTotal);
    const each = remainder / missing.length;
    for (const z of missing) z.size = each;
  }
  // If assigned sizes exceed 100, scale them down proportionally.
  const sumNow = out.reduce((acc, z) => acc + z.size, 0);
  if (sumNow > 100) {
    const scale = 100 / sumNow;
    for (const z of out) z.size *= scale;
  }
  return out;
});

const drawerVisible = computed(() => {
  const p = preset.value;
  if (!p) return false;
  const z = p.zones?.drawer;
  if (!z || z.visible === false) return false;
  const slots = p.slots?.filter((s) => s.zoneId === "drawer") || [];
  return slots.length > 0 || props.showEmpty;
});

const statusBarVisible = computed(() => {
  const p = preset.value;
  if (!p) return false;
  const z = p.zones?.["status-bar"];
  if (!z || z.visible === false) return false;
  const slots = p.slots?.filter((s) => s.zoneId === "status-bar") || [];
  return slots.length > 0 || props.showEmpty;
});

/** Which zone currently hosts the chat slot (or null). */
const chatZoneId = computed(() => {
  const p = preset.value;
  if (!p) return null;
  const s = (p.slots || []).find((slot) => slot.panelId === "chat");
  return s?.zoneId || null;
});

/** True iff the active preset has a `chat` slot anywhere. */
const chatSlotActive = computed(() => chatZoneId.value != null);

/** Teleport target selector matching the ZoneSlot placeholder id. The
 *  selector varies by zone so Vue's Teleport re-queries on every move. */
const chatMountSelector = computed(() => {
  const zone = chatZoneId.value || "none";
  return `#kt-teleport-chat-${props.instanceId || "global"}-${zone}`;
});

function zoneComponentFor(type) {
  switch (type) {
    case "sidebar":
      return ZoneSidebar;
    case "main":
      return ZoneMain;
    case "aux":
      return ZoneAux;
    default:
      return ZoneMain;
  }
}

function onHorizontalResize(sizes) {
  // sizes is an array of `{size: number}` objects from splitpanes,
  // aligned with horizontalPanes order. Persist via layout store so the
  // user's drag sticks across reloads (scoped to current instance).
  if (!Array.isArray(sizes)) return;
  const panes = horizontalPanes.value;
  if (sizes.length !== panes.length) return;
  for (let i = 0; i < panes.length; i++) {
    const { zoneId } = panes[i];
    const newSize = Number(sizes[i].size);
    if (!Number.isFinite(newSize)) continue;
    layout.setSlotSize(zoneId, newSize);
  }
}

// Save-as-new modal open state. Triggered by the preset strip's "+"
// button and the edit-mode banner's "Save as new" button via events.
const saveModalOpen = ref(false);
let unsubSaveAs = () => {};

function onSaved() {
  // After saving a preset the store already switched to it. Exit edit
  // mode if we were in one.
  if (layout.editMode) layout.exitEditMode();
}

onMounted(() => {
  if (props.instanceId) {
    layout.loadInstanceOverrides(props.instanceId);
  }
  unsubSaveAs = onLayoutEvent(LAYOUT_EVENTS.SAVE_AS_REQUESTED, () => {
    saveModalOpen.value = true;
  });
  if (typeof window !== "undefined") {
    window.addEventListener("resize", onResize);
  }
});

onUnmounted(() => {
  unsubSaveAs();
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", onResize);
  }
});
</script>

<style scoped>
.workspace-shell__zones {
  height: 100%;
  width: 100%;
}
</style>
