<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-800">收款确认</h2>
      <span class="text-xs text-gray-400">财务视角：待确认收款 → 确认后工单转为 paid</span>
    </div>

    <div v-if="error" class="bg-red-50 text-red-600 text-sm px-4 py-2 rounded-lg">{{ error }}</div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="text-left px-4 py-2">工单号</th>
            <th class="text-left px-4 py-2">租户</th>
            <th class="text-left px-4 py-2">产品</th>
            <th class="text-left px-4 py-2">档位/席位</th>
            <th class="text-left px-4 py-2">状态</th>
            <th class="text-left px-4 py-2">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in filtered" :key="t.id" class="border-t border-gray-100">
            <td class="px-4 py-2 font-mono text-xs">{{ t.ticket_no }}</td>
            <td class="px-4 py-2">{{ t.tenant_name }}</td>
            <td class="px-4 py-2">{{ t.product }}</td>
            <td class="px-4 py-2">{{ t.tier || '-' }} / {{ t.seats || '-' }}</td>
            <td class="px-4 py-2">
              <span :class="statusClass(t.status)">{{ statusText(t.status) }}</span>
            </td>
            <td class="px-4 py-2">
              <button
                v-if="t.status === 'pending'"
                @click="doConfirm(t)"
                class="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
              >确认收款</button>
              <span v-else class="text-xs text-gray-400">已确认</span>
            </td>
          </tr>
          <tr v-if="!filtered.length"><td colspan="6" class="px-4 py-6 text-center text-gray-400">无工单</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { cloudApi, extractError } from "../../api/cloud-auth";
import type { LicenseTicket } from "../../types/auth";

const tickets = ref<LicenseTicket[]>([]);
const error = ref("");

const filtered = computed(() =>
  tickets.value.filter((t) => ["pending", "paid"].includes(t.status))
);

async function load() {
  error.value = "";
  try {
    const res = await cloudApi.listTickets();
    const data = res.data?.data ?? res.data;
    tickets.value = Array.isArray(data) ? data : (data?.data ?? []);
  } catch (e: any) {
    error.value = extractError(e);
  }
}

async function doConfirm(t: LicenseTicket) {
  try {
    await cloudApi.financeConfirmTicket(t.id);
    await load();
  } catch (e: any) {
    error.value = extractError(e);
  }
}

function statusText(s: string) {
  return s === "paid" ? "已收款" : s === "pending" ? "待确认收款" : s;
}
function statusClass(s: string) {
  return s === "paid"
    ? "text-green-600 font-medium"
    : s === "pending"
    ? "text-amber-600 font-medium"
    : "text-gray-500";
}

onMounted(load);
</script>
