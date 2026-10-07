<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-800">实例 / 验签</h2>
      <span class="text-xs text-gray-400">运维视角：私有化实例凭证有效性（实时心跳属 P2 后续）</span>
    </div>

    <div v-if="error" class="bg-red-50 text-red-600 text-sm px-4 py-2 rounded-lg">{{ error }}</div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="text-left px-4 py-2">租户</th>
            <th class="text-left px-4 py-2">产品</th>
            <th class="text-left px-4 py-2">档位/席位</th>
            <th class="text-left px-4 py-2">凭证(前8位)</th>
            <th class="text-left px-4 py-2">签发时间</th>
            <th class="text-left px-4 py-2">到期</th>
            <th class="text-left px-4 py-2">剩余天数</th>
            <th class="text-left px-4 py-2">验签</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in instances" :key="i.ticket_id" class="border-t border-gray-100">
            <td class="px-4 py-2">{{ i.tenant_name }}</td>
            <td class="px-4 py-2">{{ i.product }}</td>
            <td class="px-4 py-2">{{ i.tier || '-' }} / {{ i.seats || '-' }}</td>
            <td class="px-4 py-2 font-mono text-xs">{{ i.license_key_hint }}</td>
            <td class="px-4 py-2 text-xs">{{ i.issued_at || '-' }}</td>
            <td class="px-4 py-2 text-xs">{{ i.expires_at || '-' }}</td>
            <td class="px-4 py-2">
              <span :class="i.warning ? 'text-amber-600 font-medium' : 'text-gray-600'">
                {{ i.days_left != null ? i.days_left + ' 天' : '-' }}
              </span>
            </td>
            <td class="px-4 py-2">
              <span :class="i.valid ? 'text-green-600' : 'text-red-600'">
                {{ i.valid ? '有效' : '失效' }}
              </span>
              <span v-if="i.error" class="block text-xs text-red-400">{{ i.error }}</span>
            </td>
          </tr>
          <tr v-if="!instances.length"><td colspan="8" class="px-4 py-6 text-center text-gray-400">无私有化实例</td></tr>
        </tbody>
      </table>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h3 class="text-sm font-medium text-gray-700 mb-2">手动验签自检</h3>
      <div class="flex gap-2">
        <input
          v-model="probeKey"
          placeholder="粘贴 license key"
          class="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
        />
        <button @click="probe" class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">验签</button>
      </div>
      <div v-if="probeResult" class="mt-2 text-sm" :class="probeResult.valid ? 'text-green-600' : 'text-red-600'">
        {{ probeResult.valid ? '有效：' + JSON.stringify(probeResult.claims) : '失效：' + probeResult.error }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { cloudApi, extractError } from "../../api/cloud-auth";

interface InstanceRow {
  ticket_id: string;
  tenant_name: string;
  product: string;
  tier?: string;
  seats?: number;
  license_key_hint: string | null;
  issued_at: string | null;
  expires_at: string | null;
  days_left: number | null;
  valid: boolean;
  error: string | null;
  warning: boolean;
}

const instances = ref<InstanceRow[]>([]);
const error = ref("");
const probeKey = ref("");
const probeResult = ref<any>(null);

async function load() {
  error.value = "";
  try {
    const res = await cloudApi.listInstances();
    const data = res.data?.data ?? res.data;
    instances.value = Array.isArray(data) ? data : [];
  } catch (e: any) {
    error.value = extractError(e);
  }
}

async function probe() {
  if (!probeKey.value) return;
  probeResult.value = null;
  try {
    const res = await cloudApi.verifyLicenseKey(probeKey.value);
    probeResult.value = res.data?.data ?? res.data;
  } catch (e: any) {
    probeResult.value = { valid: false, error: extractError(e) };
  }
}

onMounted(load);
</script>
