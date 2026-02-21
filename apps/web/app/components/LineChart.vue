<script setup>
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { Line } from "vue-chartjs";

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
ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale, Filler);

const chartData = computed(() => props.data);
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  ...props.options,
}));
</script>

<template>
  <Line :data="chartData" :options="chartOptions" />
</template>
