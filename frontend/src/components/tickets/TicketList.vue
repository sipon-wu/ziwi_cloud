<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h2 class="text-base font-semibold text-gray-800">
        {{ scope === "mine" ? "我的工单" : "License 工单" }}
      </h2>
      <div class="flex gap-2 items-center">
        <select v-model="statusFilter" @change="load" class="text-sm border border-gray-300 rounded-lg px-2 py-1 outline-none">
          <option value="">全部状态</option>
          <option v-for="(lbl, key) in STATUS_LABELS" :key="key" :value="key">{{ lbl }}</option>
        </select>
        <button v-if="canCreate" @click="showCreate = !showCreate" class="text-sm bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700">
          {{ showCreate ? "收起" : "新建工单" }}
        </button>
        <button @click="load" :disabled="loading" class="text-sm text-blue-600 hover:underline disabled:opacity-50">刷新</button>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 text-red-600 text-sm px-4 py-2 rounded-lg">{{ error }}</div>

    <!-- 新建工单表单 -->
    <section v-if="canCreate && showCreate" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div v-if="createError" class="bg-red-50 text-red-600 text-sm px-4 py-2 rounded-lg">{{ createError }}</div>
      <div v-if="createOk" class="bg-green-50 text-green-700 text-sm px-4 py-2 rounded-lg">{{ createOk }}</div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">租户 ID*</label>
          <input v-model="form.tenant_id" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">租户名称*</label>
          <input v-model="form.tenant_name" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">产品*</label>
          <select v-model="form.product" class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500">
            <option value="school">school</option>
            <option value="mfg">mfg</option>
            <option value="ecms">ecms</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">工单类型*</label>
          <select v-model="form.ticket_type" class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500">
            <option value="new">新开 (new)</option>
            <option value="renewal">续费 (renewal)</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">档位</label>
          <select v-model="form.tier" class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">—</option>
            <option value="basic">basic</option>
            <option value="pro">pro</option>
            <option value="flagship">flagship</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">席位/学校数</label>
          <input v-model.number="form.seats" type="number" min="1" class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">部署模式</label>
          <select v-model="form.deploy_mode" class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500">
            <option value="saas">saas</option>
            <option value="private">private</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">域名绑定（离线证）</label>
          <input v-model="form.domain" type="text" placeholder="如 yzxgn.ecms.ziwi.cn，留空=不绑定"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">到期时间*</label>
          <input v-model="form.requested_expires_at" type="datetime-local" required class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">备注</label>
        <textarea v-model="form.remarks" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"></textarea>
      </div>
      <button @click="create" :disabled="creating" class="bg-blue-600 hover:bg-blue-700 text-white font-medium px-5 py-2 rounded-lg disabled:opacity-50">
        {{ creating ? "提交中..." : "提交工单" }}
      </button>
    </section>

    <!-- 工单表格 -->
    <section class="bg-white rounded-xl border border-gray-200 p-5 overflow-x-auto">
      <table class="w-full text-sm min-w-[720px]">
        <thead>
          <tr class="text-left text-gray-500 border-b border-gray-100">
            <th class="py-2">工单号</th>
            <th>租户</th>
            <th>产品</th>
            <th>类型</th>
            <th>档位</th>
            <th>席位</th>
            <th>状态</th>
            <th>到期</th>
            <th>域名</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.id" class="border-b border-gray-50">
            <td class="py-2">{{ t.ticket_no }}</td>
            <td>{{ t.tenant_name }}</td>
            <td>{{ t.product }}</td>
            <td>{{ t.ticket_type }}</td>
            <td>{{ t.tier || "—" }}</td>
            <td>{{ t.seats ?? "—" }}</td>
            <td><span class="px-2 py-0.5 rounded bg-gray-100 text-gray-600 text-xs">{{ STATUS_LABELS[t.status] || t.status }}</span></td>
            <td class="text-xs text-gray-500">{{ fmt(t.requested_expires_at) }}</td>
            <td class="text-xs text-gray-500">{{ t.domain || "—" }}</td>
            <td class="space-x-2 whitespace-nowrap">
              <button v-if="canApprove && t.status === 'paid'" @click="openApprove(t)" class="text-sm text-blue-600 hover:underline">审批</button>
              <button v-if="canApprove && ['pending', 'paid', 'approved'].includes(t.status)" @click="openReject(t)" class="text-sm text-red-600 hover:underline">驳回</button>
              <button v-if="canApprove && t.status === 'approved' && !t.has_license_key" @click="issueKey(t)" class="text-sm text-green-600 hover:underline">签发key</button>
              <button v-if="canApprove && t.has_license_key" @click="openKey(t)" class="text-sm text-gray-700 hover:underline">查看key</button>
              <button v-if="canApprove && t.status === 'approved'" @click="openRenew(t)" class="text-sm text-amber-600 hover:underline">续期</button>
            </td>
          </tr>
          <tr v-if="!tickets.length">
            <td colspan="10" class="py-4 text-center text-gray-400">暂无工单</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- 弹层：key / 续期 / 驳回 / 审批 -->
    <div v-if="modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 space-y-4">
        <div class="flex items-start justify-between">
          <h3 class="text-base font-semibold text-gray-800">{{ modalTitle }}</h3>
          <button @click="modal = null" class="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <!-- License key -->
        <template v-if="modal === 'key'">
          <div class="text-xs text-gray-500 space-y-1">
            <div>工单：{{ keyInfo.ticket_no }}　租户：{{ keyInfo.tenant_id }}</div>
            <div>到期：{{ fmt(keyInfo.expires_at) }}　长度：{{ (keyInfo.license_key || "").length }} 字符</div>
          </div>
          <textarea readonly :value="keyInfo.license_key" rows="6"
            class="w-full font-mono text-[11px] break-all border border-gray-300 rounded-lg p-3 bg-gray-50"></textarea>
          <div class="flex items-center gap-2">
            <button @click="copyKey" class="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700">复制</button>
            <button @click="downloadKey" class="text-sm border border-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-50">下载 .key</button>
            <span v-if="copied" class="text-xs text-green-600">已复制</span>
          </div>
          <p class="text-xs text-amber-600">
            凭据明文点到点交付，勿入 Git / 工单备注 / 日志；交付后请对方回 ack（长度 + sha256 前 8 位）。
            续期请走「续期」按钮，勿对已有证的工单重复签发（已做幂等保护，不会覆盖）。
          </p>
        </template>

        <!-- 续期 -->
        <template v-else-if="modal === 'renew'">
          <div class="text-xs text-gray-500">
            续期对象：{{ renewForm.tenant_id }} / {{ renewForm.product }}
            （以该租户该产品最近一张已审批工单为基线）
          </div>
          <div>
            <label class="block text-sm text-gray-700 mb-1">新到期时间*</label>
            <input v-model="renewForm.new_expires_at" type="datetime-local"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm text-gray-700 mb-1">备注</label>
            <input v-model="renewForm.remarks" type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <p class="text-xs text-gray-500">
            域名绑定将从基线工单继承（{{ renewForm.domain || "无" }}）。
            续期会生成新的 renewal 工单，仍需：财务确认 → 审批 → 签发新证；旧证到期自然失效。
          </p>
          <div v-if="modalError" class="bg-red-50 text-red-600 text-sm px-3 py-2 rounded-lg">{{ modalError }}</div>
          <button @click="doRenew" :disabled="modalBusy"
            class="bg-amber-600 hover:bg-amber-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">
            {{ modalBusy ? "提交中..." : "确认续期" }}
          </button>
        </template>

        <!-- 驳回 -->
        <template v-else-if="modal === 'reject'">
          <div class="text-xs text-gray-500">驳回工单：{{ rejectTarget.ticket_no }}（{{ rejectTarget.tenant_name }}）</div>
          <textarea v-model="rejectReason" rows="3" placeholder="请填写驳回原因（必填，会写入工单备注）"
            class="w-full border border-gray-300 rounded-lg p-3 text-sm outline-none focus:ring-2 focus:ring-red-400"></textarea>
          <div v-if="modalError" class="bg-red-50 text-red-600 text-sm px-3 py-2 rounded-lg">{{ modalError }}</div>
          <button @click="doReject" :disabled="modalBusy"
            class="bg-red-600 hover:bg-red-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">
            {{ modalBusy ? "提交中..." : "确认驳回" }}
          </button>
        </template>

        <!-- 审批 -->
        <template v-else-if="modal === 'approve'">
          <div class="text-xs text-gray-500">审批工单：{{ approveTarget.ticket_no }}（{{ approveTarget.tenant_name }}）</div>
          <textarea v-model="approveRemarks" rows="2" placeholder="审批意见（可选）"
            class="w-full border border-gray-300 rounded-lg p-3 text-sm outline-none focus:ring-2 focus:ring-blue-400"></textarea>
          <div v-if="modalError" class="bg-red-50 text-red-600 text-sm px-3 py-2 rounded-lg">{{ modalError }}</div>
          <button @click="doApprove" :disabled="modalBusy"
            class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">
            {{ modalBusy ? "提交中..." : "确认通过" }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import { cloudApi, extractError } from "../../api/cloud-auth";

defineProps<{ scope: "all" | "mine"; canCreate: boolean }>();
const auth = useAuthStore();

const STATUS_LABELS: Record<string, string> = {
  pending: "待支付",
  paid: "待审批",
  approved: "已通过",
  rejected: "已驳回",
  completed: "已完成",
};

// 仅运营 / 超管可执行审批与签发
const canApprove = computed(() => auth.roles.includes("operator") || auth.isSuperAdmin());

const tickets = ref<any[]>([]);
const loading = ref(false);
const error = ref("");
const statusFilter = ref("");

const showCreate = ref(false);
const form = ref({
  tenant_id: "",
  tenant_name: "",
  product: "school",
  ticket_type: "new",
  tier: "",
  seats: null as number | null,
  deploy_mode: "saas",
  domain: "",
  requested_expires_at: "",
  remarks: "",
});
const creating = ref(false);
const createError = ref("");
const createOk = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await cloudApi.listTickets({ status_filter: statusFilter.value || undefined });
    tickets.value = (res.data?.data ?? res.data) || [];
  } catch (e: any) {
    error.value = extractError(e);
  } finally {
    loading.value = false;
  }
}

async function create() {
  creating.value = true;
  createError.value = "";
  createOk.value = "";
  try {
    const payload: any = { ...form.value };
    if (!payload.tier) delete payload.tier;
    if (payload.seats == null) delete payload.seats;
    if (payload.requested_expires_at) {
      payload.requested_expires_at = new Date(payload.requested_expires_at).toISOString();
    }
    await cloudApi.createTicket(payload);
    createOk.value = "工单已提交";
    showCreate.value = false;
    form.value = {
      tenant_id: "", tenant_name: "", product: "school", ticket_type: "new",
      tier: "", seats: null, deploy_mode: "saas", domain: "", requested_expires_at: "", remarks: "",
    };
    await load();
  } catch (e: any) {
    createError.value = extractError(e);
  } finally {
    creating.value = false;
  }
}

// ── 弹层状态（签发/查看 key、续期、驳回、审批）──
const modal = ref<null | "key" | "renew" | "reject" | "approve">(null);
const modalTitle = computed(() => {
  if (modal.value === "key") return "License Key";
  if (modal.value === "renew") return "License 续期";
  if (modal.value === "reject") return "驳回工单";
  return "审批工单";
});
const modalBusy = ref(false);
const modalError = ref("");
const copied = ref(false);

const keyInfo = ref<any>({});
const approveTarget = ref<any>({});
const approveRemarks = ref("");
const rejectTarget = ref<any>({});
const rejectReason = ref("");
const renewForm = ref({
  tenant_id: "", product: "", domain: "", new_expires_at: "", remarks: "",
});

function openApprove(t: any) {
  modalError.value = "";
  approveRemarks.value = "";
  approveTarget.value = t;
  modal.value = "approve";
}

async function doApprove() {
  modalBusy.value = true;
  modalError.value = "";
  try {
    await cloudApi.approveTicket(approveTarget.value.id, approveRemarks.value);
    modal.value = null;
    await load();
  } catch (e: any) {
    modalError.value = extractError(e);
  } finally {
    modalBusy.value = false;
  }
}

// 签发：必须把返回值接住，否则 key 只存在于响应里，关掉就再也拿不到
async function issueKey(t: any) {
  try {
    const res = await cloudApi.issueLicenseKey(t.id);
    keyInfo.value = res.data?.data ?? res.data;
    copied.value = false;
    modal.value = "key";
    await load();
  } catch (e: any) {
    error.value = extractError(e);
  }
}

// 只读取回已签发的 key（不重签、不改 claims）
async function openKey(t: any) {
  try {
    const res = await cloudApi.getLicenseKey(t.id);
    keyInfo.value = res.data?.data ?? res.data;
    copied.value = false;
    modalError.value = "";
    modal.value = "key";
  } catch (e: any) {
    error.value = extractError(e);
  }
}

async function copyKey() {
  try {
    await navigator.clipboard.writeText(keyInfo.value.license_key || "");
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    error.value = "浏览器拒绝剪贴板，请手动选中文本复制";
  }
}

function downloadKey() {
  const text = keyInfo.value.license_key || "";
  // 不带换行：与平台侧 sha256 计算口径一致
  const blob = new Blob([text], { type: "text/plain;charset=ascii" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${keyInfo.value.ticket_no || "license"}.key`;
  a.click();
  URL.revokeObjectURL(url);
}

function openRenew(t: any) {
  modalError.value = "";
  renewForm.value = {
    tenant_id: t.tenant_id, product: t.product, domain: t.domain || "",
    new_expires_at: "", remarks: "",
  };
  modal.value = "renew";
}

async function doRenew() {
  modalBusy.value = true;
  modalError.value = "";
  try {
    const payload: any = {
      tenant_id: renewForm.value.tenant_id,
      product: renewForm.value.product,
      new_expires_at: new Date(renewForm.value.new_expires_at).toISOString(),
    };
    if (renewForm.value.remarks) payload.remarks = renewForm.value.remarks;
    await cloudApi.renewLicense(payload);
    modal.value = null;
    await load();
  } catch (e: any) {
    modalError.value = extractError(e);
  } finally {
    modalBusy.value = false;
  }
}

function openReject(t: any) {
  modalError.value = "";
  rejectReason.value = "";
  rejectTarget.value = t;
  modal.value = "reject";
}

async function doReject() {
  modalBusy.value = true;
  modalError.value = "";
  try {
    await cloudApi.rejectTicket(rejectTarget.value.id, rejectReason.value);
    modal.value = null;
    await load();
  } catch (e: any) {
    modalError.value = extractError(e);
  } finally {
    modalBusy.value = false;
  }
}

function fmt(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("zh-CN");
  } catch {
    return iso;
  }
}

onMounted(load);
</script>
