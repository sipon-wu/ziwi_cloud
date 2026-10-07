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
            <td class="space-x-2 whitespace-nowrap">
              <button v-if="canApprove && t.status === 'pending'" @click="approve(t)" class="text-sm text-blue-600 hover:underline">审批</button>
              <button v-if="canApprove && t.status === 'approved' && !t.has_license_key" @click="issueKey(t)" class="text-sm text-green-600 hover:underline">签发key</button>
              <span v-if="t.has_license_key" class="text-xs text-gray-400">已签发</span>
            </td>
          </tr>
          <tr v-if="!tickets.length">
            <td colspan="9" class="py-4 text-center text-gray-400">暂无工单</td>
          </tr>
        </tbody>
      </table>
    </section>
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
    const res = await cloudApi.listTickets({ status: statusFilter.value || undefined });
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
      tier: "", seats: null, deploy_mode: "saas", requested_expires_at: "", remarks: "",
    };
    await load();
  } catch (e: any) {
    createError.value = extractError(e);
  } finally {
    creating.value = false;
  }
}

async function approve(t: any) {
  try {
    await cloudApi.approveTicket(t.id, "");
    await load();
  } catch (e: any) {
    error.value = extractError(e);
  }
}

async function issueKey(t: any) {
  try {
    await cloudApi.issueLicenseKey(t.id);
    await load();
  } catch (e: any) {
    error.value = extractError(e);
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
