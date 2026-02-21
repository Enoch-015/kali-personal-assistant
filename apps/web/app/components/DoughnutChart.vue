<script setup>
import {
  ArcElement,
  Chart as ChartJS,
  Legend,
  Title,
  Tooltip,
} from "chart.js";
import { Doughnut } from "vue-chartjs";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  options: {
    type: Object,
    default: () => ({}),
  },
});

// Register Chart.js components
ChartJS.register(Title, Tooltip, Legend, ArcElement);

const chartData = computed(() => props.data);
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  ...props.options,
}));
</script>

<template>
  <Doughnut :data="chartData" :options="chartOptions" />
</template>
