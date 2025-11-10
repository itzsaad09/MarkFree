function simulateProgress(progressBarId, targetPercentage, duration, callback) {
  const progressBar = document.getElementById(progressBarId);
  let progress = 0;
  const increment = targetPercentage / (duration / 100);

  const interval = setInterval(() => {
    progress += increment;
    if (progress >= targetPercentage) {
      progress = targetPercentage;
      clearInterval(interval);
      progressBar.style.width = `${progress}%`;
      if (callback) callback();
    } else {
      progressBar.style.width = `${progress}%`;
    }
  }, 100);
}