<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-gray-800">知微云 · 租户自助中心</h1>
        <p class="text-sm text-gray-500">
          当前账号：{{ auth.user?.email || tenant.email || '—' }}
          <span class="ml-2 px-2 py-0.5 rounded bg-green-100 text-green-700 text-xs">租户管理</span>
        </p>
      </div>
      <button @click="doLogout" class="text-sm text-gray-500 hover:text-gray-800">退出登录</button>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-10 space-y-8">
      <!-- 租户基本信息 -->
      <section class="bg-white rounded-xl border border-gray-200 p-6">
        <h2 class="text-base font-semibold text-gray-800 mb-4">租户信息</h2>
        <div v-if="loading" class="text-sm text-gray-400">加载中…</div>
        <div v-else class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-gray-500">租户 ID</p>
            <p class="text-gray-800 font-medium break-all">{{ tenant.tenant_id || '—' }}</p>
          </div>
          <div>
            <p class="text-gray-500">开通产品</p>
            <p class="text-gray-800 font-medium">{{ (tenant.products || []).join('、') || '—' }}</p>
          </div>
        </div>
      </section>

      <!-- License 授权 -->
      <section class="bg-white rounded-xl border border-gray-200 p-6">
        <h2 class="text-base font-semibold text-gray-800 mb-4">License 授权</h2>
        <div v-if="loading" class="text-sm text-gray-400">加载中…</div>
        <div v-else-if="tickets.length === 0" class="text-sm text-gray-400">暂无 License 授权记录</div>
        <div v-else class="space-y-3">
          <div v-for="t in tickets" :key="t.id" class="border border-gray-100 rounded-lg p-4 flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-800">
                {{ productLabel(t.product) }}
                <span class="text-gray-400 text-xs">（{{ t.ticket_no }}）</span>
              </p>
              <p class="text-sm text-gray-500 mt-1">
                有效期至：{{ t.current_expires_at || t.requested_expires_at || '—' }}
                <span v-if="t.seats" class="ml-3">席位：{{ t.seats }}</span>
              </p>
            </div>
            <span :class="statusClass(t.status)" class="px-2 py-1 rounded text-xs whitespace-nowrap">{{ statusLabel(t.status) }}</span>
          </div>
        </div>
      </section>

      <!-- 账单 / 发票 占位 -->
      <section class="bg-white rounded-xl border border-dashed border-gray-200 p-6 text-center text-gray-400">
        <p class="text-sm">账单 / 发票 自助功能建设中。</p>
      </section>

      <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { cloudApi } from "../api/cloud-auth";

const router = useRouter();
const auth = useAuthStore();

const loading = ref(true);
const error = ref("");
const tenant = ref<any>({ tenant_id: "", email: "", products: [] });
const tickets = ref<any[]>([]);

function productLabel(p: string): string {
  const m: Record<string, string> = {
    school: "知微 AI 教学助手",
    mfg: "智能制造",
    ecms: "能碳管理",
  };
  return m[p] || p;
}
function statusLabel(s: string): string {
  const m: Record<string, string> = {
    approved: "已激活",
    pending: "待审核",
    rejected: "已驳回",
    expired: "已过期",
  };
  return m[s] || s;
}
function statusClass(s: string): string {
  if (s === "approved") return "bg-green-100 text-green-700";
  if (s === "pending") return "bg-yellow-100 text-yellow-700";
  if (s === "rejected") return "bg-red-100 text-red-700";
  return "bg-gray-100 text-gray-600";
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [meRes, tkRes] = await Promise.all([
      cloudApi.tenantMe(),
      cloudApi.tenantTickets(),
    ]);
    tenant.value = meRes.data || tenant.value;
    tickets.value = tkRes.data || [];
  } catch (e: any) {
    error.value = e?.userMessage || e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

function doLogout() {
  auth.logout();
  router.push("/login");
}

onMounted(load);
</script>
