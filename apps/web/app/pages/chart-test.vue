<script setup>
// Total Users line chart data
const totalUsersData = {
  labels: ["", "", "", "", "", "", "", "", "", "", "", ""],
  datasets: [{
    data: [45, 52, 48, 61, 55, 67, 60, 70, 65, 59, 68, 75],
    borderColor: "#3b82f6",
    backgroundColor: "rgba(59, 130, 246, 0.1)",
    fill: true,
    tension: 0.4,
    pointRadius: 0,
  }, {
    data: [40, 45, 42, 50, 48, 55, 52, 58, 54, 52, 56, 60],
    borderColor: "rgba(148, 163, 184, 0.5)",
    borderDash: [5, 5],
    fill: false,
    tension: 0.4,
    pointRadius: 0,
  }],
};

// Active Users doughnut data
const activeUsersData = {
  labels: ["Active", "Inactive"],
  datasets: [{
    data: [78, 22],
    backgroundColor: ["#3b82f6", "#1e293b"],
    borderWidth: 0,
    cutout: "75%",
  }],
};

// Revenue sparkline data
const revenueSparkData = {
  labels: ["", "", "", "", "", "", ""],
  datasets: [{
    data: [3200, 3800, 3500, 4100, 3900, 4200, 4300],
    borderColor: "#3b82f6",
    backgroundColor: "rgba(59, 130, 246, 0.1)",
    fill: true,
    tension: 0.4,
    pointRadius: 0,
  }],
};

// New Clients sparkline data
const newClientsData = {
  labels: ["", "", "", "", "", "", ""],
  datasets: [{
    data: [6500, 6800, 6600, 6900, 6700, 6750, 6782],
    borderColor: "#3b82f6",
    backgroundColor: "transparent",
    fill: false,
    tension: 0.4,
    pointRadius: 0,
  }],
};

// Active Subscriptions dual line data
const subscriptionsData = {
  labels: ["", "", "", "", "", "", ""],
  datasets: [{
    data: [2800, 2850, 2900, 2920, 2950, 2970, 2986],
    borderColor: "#3b82f6",
    backgroundColor: "rgba(59, 130, 246, 0.1)",
    fill: true,
    tension: 0.4,
    pointRadius: 0,
  }, {
    data: [2750, 2800, 2820, 2860, 2880, 2900, 2940],
    borderColor: "rgba(148, 163, 184, 0.5)",
    fill: false,
    tension: 0.4,
    pointRadius: 0,
  }],
};

// Shared sparkline options
const sparklineOptions = {
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  },
  scales: {
    x: {
      display: false,
      grid: { display: false },
    },
    y: {
      display: false,
      grid: { display: false },
    },
  },
};

// Doughnut chart options
const doughnutOptions = {
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  },
};

// Dual line options (same as sparkline)
const dualLineOptions = {
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  },
  scales: {
    x: {
      display: false,
      grid: { display: false },
    },
    y: {
      display: false,
      grid: { display: false },
    },
  },
};
</script>

<template>
  <div class="flex min-h-screen flex-col bg-[#0f172a]">
    <main class="mx-auto w-full max-w-[1400px] flex-1 px-3 py-6 sm:px-6">
      <!-- Top Row -->
      <div class="grid gap-4 mb-4 lg:grid-cols-12">
        <!-- Welcome Card -->
        <section class="lg:col-span-5 rounded-xl bg-[#1e293b] p-5">
          <div class="flex justify-between">
            <div>
              <h2 class="text-xl font-semibold text-white">
                Welcome back, Pawel
              </h2>
              <p class="text-sm text-slate-400 mt-1">
                You have 5 new messages and 2 new notifications.
              </p>
            </div>
            <div class="w-24 h-24 flex-shrink-0">
              <!-- Illustration placeholder -->
              <div class="w-full h-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full flex items-center justify-center">
                <Icon name="tabler-user-check" class="text-4xl text-blue-400" />
              </div>
            </div>
          </div>
          <div class="flex gap-8 mt-6">
            <div>
              <p class="text-xs text-slate-500 uppercase tracking-wide">
                Today's Sales
              </p>
              <div class="flex items-baseline gap-2 mt-1">
                <span class="text-2xl font-bold text-white">6,782</span>
                <span class="text-xs text-emerald-400 flex items-center gap-0.5">
                  7% <Icon name="tabler-trending-up" class="text-sm" />
                </span>
              </div>
              <div class="h-1 w-20 bg-emerald-500 rounded-full mt-2" />
            </div>
            <div>
              <p class="text-xs text-slate-500 uppercase tracking-wide">
                Growth Rate
              </p>
              <div class="flex items-baseline gap-2 mt-1">
                <span class="text-2xl font-bold text-white">78.4%</span>
                <span class="text-xs text-rose-400 flex items-center gap-0.5">
                  -1% <Icon name="tabler-trending-down" class="text-sm" />
                </span>
              </div>
              <div class="h-1 w-20 bg-rose-500 rounded-full mt-2" />
            </div>
          </div>
        </section>

        <!-- Total Users Card -->
        <section class="lg:col-span-4 rounded-xl bg-[#1e293b] p-5">
          <p class="text-xs text-slate-500 uppercase tracking-wide">
            Total Users
          </p>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-3xl font-bold text-white">75,782</span>
            <span class="text-xs text-emerald-400 flex items-center gap-0.5">
              2% <Icon name="tabler-trending-up" class="text-sm" />
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-1">
            24,635 users increased from last month
          </p>
          <div class="h-20 mt-3">
            <LineChart :data="totalUsersData" :options="sparklineOptions" />
          </div>
        </section>

        <!-- Active Users Card -->
        <section class="lg:col-span-3 rounded-xl bg-[#1e293b] p-5">
          <p class="text-xs text-slate-500 uppercase tracking-wide">
            Active Users
          </p>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-3xl font-bold text-white">25,782</span>
            <span class="text-xs text-rose-400 flex items-center gap-0.5">
              -1% <Icon name="tabler-trending-down" class="text-sm" />
            </span>
          </div>
          <div class="h-28 mt-2 relative flex items-center justify-center">
            <DoughnutChart :data="activeUsersData" :options="doughnutOptions" />
            <span class="absolute text-xl font-bold text-white">78%</span>
          </div>
        </section>
      </div>

      <!-- Bottom Row -->
      <div class="grid gap-4 lg:grid-cols-4">
        <!-- Sales Card -->
        <section class="rounded-xl bg-[#1e293b] p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-slate-500 uppercase tracking-wide">
              Sales
            </p>
            <button class="text-xs text-slate-400 flex items-center gap-1">
              Last 7 days <Icon name="tabler-chevron-down" />
            </button>
          </div>
          <div class="mt-3">
            <span class="text-4xl font-bold text-white">75%</span>
          </div>
          <div class="flex items-center gap-2 mt-4">
            <span class="text-sm text-slate-400">Conversion rate</span>
            <span class="text-xs text-emerald-400 flex items-center gap-0.5">
              7% <Icon name="tabler-trending-up" class="text-sm" />
            </span>
          </div>
        </section>

        <!-- Revenue Card -->
        <section class="rounded-xl bg-[#1e293b] p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-slate-500 uppercase tracking-wide">
              Revenue
            </p>
            <button class="text-xs text-slate-400 flex items-center gap-1">
              Last 7 days <Icon name="tabler-chevron-down" />
            </button>
          </div>
          <div class="flex items-baseline gap-2 mt-3">
            <span class="text-3xl font-bold text-white">$4,300</span>
            <span class="text-xs text-emerald-400 flex items-center gap-0.5">
              8% <Icon name="tabler-trending-up" class="text-sm" />
            </span>
          </div>
          <div class="h-16 mt-2">
            <LineChart :data="revenueSparkData" :options="sparklineOptions" />
          </div>
        </section>

        <!-- New Clients Card -->
        <section class="rounded-xl bg-[#1e293b] p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-slate-500 uppercase tracking-wide">
              New Clients
            </p>
            <button class="text-xs text-slate-400 flex items-center gap-1">
              Last 7 days <Icon name="tabler-chevron-down" />
            </button>
          </div>
          <div class="flex items-baseline gap-2 mt-3">
            <span class="text-3xl font-bold text-white">6,782</span>
            <span class="text-xs text-slate-400 flex items-center gap-0.5">
              0% —
            </span>
          </div>
          <div class="h-16 mt-2">
            <LineChart :data="newClientsData" :options="sparklineOptions" />
          </div>
        </section>

        <!-- Active Subscriptions Card -->
        <section class="rounded-xl bg-[#1e293b] p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-slate-500 uppercase tracking-wide">
              Active Subscriptions
            </p>
            <button class="text-xs text-slate-400 flex items-center gap-1">
              Last 7 days <Icon name="tabler-chevron-down" />
            </button>
          </div>
          <div class="flex items-baseline gap-2 mt-3">
            <span class="text-3xl font-bold text-white">2,986</span>
            <span class="text-xs text-emerald-400 flex items-center gap-0.5">
              4% <Icon name="tabler-trending-up" class="text-sm" />
            </span>
          </div>
          <div class="h-16 mt-2">
            <LineChart :data="subscriptionsData" :options="dualLineOptions" />
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Remove any extra spacing */
</style>
