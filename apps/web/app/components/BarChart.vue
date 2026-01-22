<script setup>
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Title,
  Tooltip,
} from "chart.js";
import { Bar } from "vue-chartjs";

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
ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale);

const chartData = computed(() => props.data);
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  ...props.options,
}));
</script>

<template>
  <Bar :data="chartData" :options="chartOptions" />
</template>
