htmlHeader = """
<!DOCTYPE html>
<html>

<head>
    <script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0"></script>
    <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
	<meta charset="utf-8">
	<title>Log Analysis Results</title>
	<script type="text/javascript">
		window.onload = function () {
			var toc = document.getElementById("toc");
			var headings = document.getElementsByTagName("h4", "h3", "h2");
			var headingArray = [];

			for (var i = 0; i < headings.length; i++) {
				var heading = headings[i];
				var anchor = document.createElement("a");
				anchor.href = "#" + heading.id;
				anchor.innerHTML = heading.innerHTML;
				var li = document.createElement("li");
				li.appendChild(anchor);
				toc.appendChild(li);

				// Store the text content and corresponding element for each heading in an array
				headingArray.push({ textContent: heading.textContent, element: li });
			}

			// Sort the array of headings by text content
			headingArray.sort((a, b) => a.textContent.localeCompare(b.textContent));
			headingArray.reverse()

			// Remove the existing list items from the table of contents
			while (toc.firstChild) {
				toc.removeChild(toc.firstChild);
			}

			// Add the sorted list items back to the table of contents
			for (var i = 0; i < headingArray.length; i++) {
				toc.appendChild(headingArray[i].element);
			}
			var rows = document.querySelectorAll("#main-table tbody tr");
			for (var i = 0; i < rows.length; i++) {
				rows[i].onclick = function () {
					var rowHeading = this.querySelector("td:nth-of-type(2)").innerHTML;
					var targetHeading = document.getElementById(rowHeading.toLowerCase().replace(/\s/g, "-").replace(/-+$/, ""));
					if (targetHeading) {
						var targetOffset = targetHeading.offsetTop - 10;
						window.scrollTo(0, targetOffset);
						// highlight the the heading and its content for 2 seconds with #C6C6C6 background color and with good animation
						targetHeading.style.backgroundColor = "#C6C6C6";
						targetHeading.style.transition = "background-color 1s ease-in-out";
						var targetContent = targetHeading.nextElementSibling;
						targetContent.style.backgroundColor = "#C6C6C6";
						targetContent.style.transition = "background-color 1s ease-in-out";
						setTimeout(function () {
							targetHeading.style.backgroundColor = "";
							targetContent.style.backgroundColor = "";
						}, 2000);
					}
				}
			}
		}
	</script>
	<style>
		body {
			font-family: 'Inter';
			background-color: #f0f0f0;
			margin-left: 20px;
			line-height: 1.5;
		}

		h2,
		h3,
  		h4{
			font-family: 'Roobert';
			margin-top: 30px;
			margin-bottom: 15px;
			margin-left: 20px;
			color: #000041;
		}

		h4 {
			font-size: 15px;
		}

		table {
			border-collapse: collapse;
			margin: auto;
			margin-top: 10px;
			margin-bottom: 30px;
			background-color: white;
			box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
			margin-left: 25px;
			margin-right: 25px;
			border-radius: 10px;
			overflow: hidden;
			transition: transform 0.2s ease-in-out;
		}

		table:hover {
			transform: scale(1.04);
		}

		th,
		td {
			padding: 10px;
			text-align: left;
			border-bottom: 1px solid #ddd;
			font-size: 15px;
			color: #2d3c4d;
			border-bottom: 1px solid #E6E8F0;
		}

		th {
			font-weight: 700;
			cursor: pointer;
			color: #000041;
			background-color: #F5F7FF;
		}

		tr:hover {
			background-color: #faf2f0;
			cursor: pointer;
		}

		a {
			color: #3A2B82;
			text-decoration: none;
			position: relative;
			left: 0;
			transition: left 0.2s ease-in-out;
		}

		a:hover {
			left: 5px;
			color: #ff6e42;
		}

		li {
			text-align: left;
		}

		p {
			margin-left: 20px;
		}

		#toc {
			position: relative;
			top: 0;
			width: auto;
			height: 100%;
			overflow: auto;
			background-color: #f0f0f0;
			margin-left: 25px;
		}
		.chart-container {
            max-width: auto;
            margin: 20px auto;
            overflow-x: auto;
            position: relative;
        }

  		canvas {
            height: 400px; /* Update the height as desired */
        }

		.popup {
			position: fixed;
			top: 50%;
			left: 50%;
			transform: translate(-50%, -50%);
			background-color: white;
			padding: 20px;
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
			display: none;
			z-index: 1;
			border-collapse: collapse;
			border-radius: 10px;
			transition: transform 0.2s ease-in-out;
			overflow: auto;
		}

        .help-message {
			font-family: Arial, sans-serif;
            line-height: 1.5;
		}
	</style>
</head>
<body>
    <div id="helpPopup" class="popup">
		<i>Welcome to the Log Analyzer Report Documentation!</i>
        <br><br>	
		<b> Chart Section </b>
		<p>In the Chart section, you can analyze the log data using interactive charts.<br>
            &nbsp;&nbsp;&nbsp;&nbsp;- To zoom in on a specific area, click and drag the cursor to select the desired region.<br>
            &nbsp;&nbsp;&nbsp;&nbsp;- To reset the zoom level, simply double-click on the chart </p>
		<b> Filtering </b>
		<p> Filtering allows you to focus on specific data in the charts.<br>
	        &nbsp;&nbsp;&nbsp;&nbsp;- To filter the data, click on the legends corresponding to the data series you want to view or hide.</p>

		<b>Logs with Issues Found</b>

		<p>The Logs with Issues Found section provides detailed information about identified issues in the logs. <br>
			&nbsp;&nbsp;&nbsp;&nbsp; - Click on a file to navigate directly to it and review the associated log entries.</p>

		<b> Table Reports</b>
		<p>The Table Reports section offers summarized views of the log data. <br>
			&nbsp;&nbsp;&nbsp;&nbsp; - To sort the table, click on the column headers. You can sort by any column <br>
            &nbsp;&nbsp;&nbsp;&nbsp; - To find solutions for errors, click on a row in the table to navigate to the corresponding solution.</p>		  
	</div>
 <script>
	document.addEventListener("keydown", function (event) {
		if (event.key === "?") {
			document.getElementById("helpPopup").style.display = "block"
		}
	});
	document.addEventListener("keydown", function (event) {
		if (event.key === "Escape") {
			document.getElementById("helpPopup").style.display = "none";
		}
	});
	window.onclick = function (event) {
		if (event.target != document.getElementById("helpPopup")) {
			document.getElementById("helpPopup").style.display = "none";
		}
	}
</script>
<div class="chart-container">
	<div class="chart-area">
		<canvas id="myChart"></canvas>
	</div>
</div>
<h3> Logs with issues found </h3>
<div id="toc">
</div>
"""   # Thanks bing for beautifying the HTML report https://tinyurl.com/2l3hskkl :)

barChart1= """
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            var data ="""

barChart2 = """
            var categories = Object.keys(data);
            var allHours = Object.values(data).flatMap(Object.keys);
            var hours = [...new Set(allHours)].sort();

            var chartData = hours.map(function(hour) {
                var dataPoints = {};
                categories.forEach(function(category) {
                    dataPoints[category] = data[category][hour] || 0;
                });
                return {
                    hour: hour,
                    dataPoints: dataPoints
                };
            });

            var datasets = categories.map(function(category, index) {
                var randomRed = Math.random() * 255;
                var randomGreen = Math.random() * 255;
                var randomBlue = Math.random() * 255;
                var backgroundColor = `rgba(${randomRed}, ${randomGreen}, ${randomBlue}, 0.6)`;
                var hoverBackgroundColor = `rgba(${randomRed}, ${randomGreen}, ${randomBlue}, 0.8)`;
                return {
                    label: category,
                    backgroundColor: backgroundColor,
                    hoverBackgroundColor: hoverBackgroundColor,
                    data: chartData.map(function(d) { return d.dataPoints[category]; })
                };
            });

            var ctx = document.getElementById("myChart").getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                xAxes: [{
                    scaleLabel: {
                        display: true,
                        labelString: 'Time'
                    }
                }],
                yAxes: [{
                    scaleLabel: {
                        display: true,
                        labelString: 'Number of Events'
                    },
                    ticks: {
                        beginAtZero: true,
                        precision: 0
                    }
                }]
            },
            hover: {
                onHover: function(e, elements) {
                    if (elements && elements.length) {
                        var index = elements[0]._index;
                        var datasetIndex = elements[0]._datasetIndex;
                        var meta = myChart.getDatasetMeta(datasetIndex);
                        meta.data.forEach(function(bar, i) {
                            if (i === index) {
                                bar._model.backgroundColor = datasets[datasetIndex].hoverBackgroundColor;
                                bar._model.borderColor = datasets[datasetIndex].hoverBackgroundColor;
                            } else {
                                bar._model.backgroundColor = datasets[datasetIndex].backgroundColor;
                                bar._model.borderColor = datasets[datasetIndex].backgroundColor;
                            }
                        });
                        myChart.update();
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    maxWidth: 500,
                    onHover: function(e) {
                        e.target.style.cursor = 'pointer';
                    },
                },
                zoom: {
                    zoom: {
                        drag: {
                            enabled: true,
                            backgroundColor: 'rgba(225,225,225,1)',
                        },
                        mode: 'xy',
                        speed: 0.05,
                    }
                }
            }
        },
    });

    var chartContainer = document.querySelector('.chart-container');
    var chartArea = document.querySelector('.chart-area');
    
    chartContainer.addEventListener('dblclick', function () {
        myChart.resetZoom();
    });
});
</script>
"""
htmlFooter = """
Credits: <a href='https://www.kryogenix.org/code/browser/sorttable/sorttable.js'> sorttable.js </a> and <a href='https://www.chartjs.org/'> Chart.js </a>
</body>
</html>
"""
