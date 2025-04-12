import yaml
import os
import json

##############################################################################
# Read log_conf.yml and parse into patterns/solutions for universe & pg
##############################################################################
config_path = os.path.join(os.path.dirname(__file__), "log_conf.yml")
with open(config_path, "r") as f:
	config = yaml.safe_load(f)

universe_config = config["universe"]["log_messages"]
pg_config = config["pg"]["log_messages"]

universe_regex_patterns = {}
universe_solutions = {}
for msg_dict in universe_config:
    name = msg_dict["name"]
    pattern = msg_dict["pattern"]
    solution = msg_dict["solution"]
    universe_regex_patterns[name] = pattern
    universe_solutions[name] = solution

pg_regex_patterns = {}
pg_solutions = {}
pg_solutions = {}
for msg_dict in pg_config:
    name = msg_dict["name"]
    pattern = msg_dict["pattern"]
    solution = msg_dict["solution"]
    pg_regex_patterns[name] = pattern
    pg_solutions[name] = solution

# Merge them for easy usage in log_analyzer
solutions = {**universe_solutions, **pg_solutions}

##############################################################################
# The rest of analyzer_lib code (HTML templates, etc.) remains the same
##############################################################################


htmlHeader = """
<!DOCTYPE html>
<html>
<head>
	<script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
	<script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0"></script>
	<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
	<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
	<script src="https://cdnjs.cloudflare.com/ajax/libs/showdown/2.1.0/showdown.min.js"></script>
 	<meta charset="utf-8">
	<title>Log Analysis Results</title>
	<script type="text/javascript">
		var solutions =""" + str(solutions) + """ ;
		htmlGenerator = new showdown.Converter();
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
				rows[i].addEventListener("click", function () {
					var message = this.cells[1].innerHTML.trim();
					var solution = solutions[message];
					// If solution is found, show popup
					if (solution) {
						var popup = document.getElementById("solutionPopup");
						var popupTitle = document.getElementById("solutionTitle");
						var popupContent = document.getElementById("solutionContent");
						var closeButton = document.getElementById("closeButton");
						popup.className = "popup";
						popup.style.display = "block";
						popup.style.zIndex = "1";
						popup.style.position = "fixed";
						popup.style.top = "50%";
						popup.style.left = "50%";
						popup.style.transform = "translate(-50%, -50%)";
						popup.style.backgroundColor = "white";
						popup.style.padding = "20px";
						popup.style.boxShadow = "0 0 10px rgba(0, 0, 0, 0.3)";
						popup.style.borderCollapse = "collapse";
						popup.style.borderRadius = "10px";
						popup.style.transition = "transform 0.2s ease-in-out";
						popup.style.overflow = "auto";
						popup.style.backgroundColor = "#eaeaea"

						// Change the size of the popup when user hovers over it
						popup.addEventListener("mouseover", function () {
							popup.style.transform = "translate(-50%, -50%) scale(1.1)";
						});
						popup.addEventListener("mouseout", function () {
							popup.style.transform = "translate(-50%, -50%)";
						});
						popupTitle.textContent = message;
						popupContent.innerHTML = htmlGenerator.makeHtml(solution);
						closeButton.addEventListener("click", function () {
							popup.style.display = "none";
						});
					}
				});
			}
		}
  
 		document.addEventListener("keydown", function (event) {
			if (event.key === "Escape") {
				document.getElementById("solutionPopup").style.display = "none";
				document.getElementById("helpPopup").style.display = "none";
			}
			else if (event.key === "h" || event.key === "H" || event.key === "?") {
				document.getElementById("helpPopup").style.display = "block";
			}
		});

		window.onclick = function (event) {
			if (event.target !== document.getElementById("helpPopup")) {
				document.getElementById("helpPopup").style.display = "none";
			}
			else if (event.target !== document.getElementById("solutionPopup")) {
				document.getElementById("solutionPopup").style.display = "none";
			}
		}

		var codeBlocks = document.querySelectorAll("code");
		window.onclick = function (event) {
		    if (event.target.matches("code")) {
		        var range = document.createRange();
		        range.selectNode(event.target);
		        window.getSelection().removeAllRanges();
		        window.getSelection().addRange(range);
		        document.execCommand("copy");
		        window.getSelection().removeAllRanges();
		    }
		}

		function closeHelpPopup() {
   			document.getElementById("helpPopup").style.display = "none";
  		}

  		function closeSolutionPopup() {
    		document.getElementById("solutionPopup").style.display = "none";
  		}  
	</script>
	<style>
		@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;700&display=swap');
		body {
			font-family: 'Rubik', sans-serif;
			background-color: #f0f0f0;
			margin-left: 20px;
			line-height: 1.5;
		}

		h2,
		h3,
		h4 {
			font-family: 'Rubik', sans-serif;
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
			border-radius: 10px;
		}

		a {
			color: #3A2B82;
			text-decoration: none;
			position: relative;
			left: 0;
			transition: left 0.2s ease-in-out;
		}

		a:hover {
			color: #ff6e42;
		}

		li {
			text-align: left;
		}

		p {
			margin-left: 20px;
		}
  
  		code {
		    background-color: #f0f0f0;
		    padding: 0.2em 0.4em;
		    margin: 0;
		    font-size: 85%;
		    border-radius: 4px;
		    font-family: 'Monospace';
		    background-color: #f6d9d0;
		    border: solid 1px #202020;
		}

		code:hover {
		    cursor: pointer;
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
			height: 400px;
			/* Update the height as desired */
		}

		.popup {
			position: fixed;
			top: 50%;
			left: 50%;
			transform: translate(-50%, -50%);
			background-color: #eaeaea;
			padding: 20px;
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
			display: none;
			z-index: 1;
			border-collapse: collapse;
			border-radius: 10px;
			transition: transform 0.2s ease-in-out;
			overflow: auto;
		}
		.warning {
			background-color: #fbf0ec;
			color: #000000;
			padding: 10px;
			margin: 20px;
			border-radius: 10px;
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);

			b {
				color: #ff6e42;
			}
		}
	</style>
</head>

<body>
	<div id="solutionPopup" class="popup">
		<button id="closeButton" onclick="closeSolutionPopup()">Close</button>
		<br>
        <h2 id="solutionTitle"></h2>
        <p id="solutionContent"></p>
    </div>
	<div id="helpPopup" class="popup">
		<button id="closeButton" onclick="closeHelpPopup()">Close</button>
		<br>
  		<i>Welcome to the Log Analyzer Report Documentation!</i>
		<br><br>
		<b> Chart Section </b>
		<p>In the Chart section, you can analyze the log data using interactive charts.<br>
			&nbsp;&nbsp;&nbsp;&nbsp;- To zoom in on a specific area, click and drag the cursor to select the desired region.<br>
			&nbsp;&nbsp;&nbsp;&nbsp;- To reset the zoom level, simply double-click on the chart </p>
		<b> Filtering </b>
		<p> Filtering allows you to focus on specific data in the charts.<br>
			&nbsp;&nbsp;&nbsp;&nbsp;- To filter the data, click on the legends corresponding to the data series you want
			to view or hide.</p>

		<b>Logs with Issues Found</b>

		<p>The Logs with Issues Found section provides detailed information about identified issues in the logs. <br>
			&nbsp;&nbsp;&nbsp;&nbsp; - Click on a file to navigate directly to it and review the associated log entries.
		</p>

		<b> Table Reports</b>
		<p>The Table Reports section offers summarized views of the log data. <br>
			&nbsp;&nbsp;&nbsp;&nbsp; - To sort the table, click on the column headers. You can sort by any column <br>
			&nbsp;&nbsp;&nbsp;&nbsp; - To find solutions for errors, click on a row in the table.</p>
		<br>

		<b> Tips </b>
			<p>	Press <b>Esc</b> to close this or troubleshooting tip popup. <br>
				Press <b>h</b>  or <b>?</b> to open the popup. <br>
				Click on code blocks to copy them to clipboard.</p>
		<br>
	</div>
	<div class="chart-container">
		<div class="chart-area">
			<canvas id="myChart"></canvas>
		</div>
	</div>
 	<div class="warning">
		<b>Warning:</b> 
		By default log_analyzer checks for logs for last 7 days. If you want to analyze older logs, Please re-run with -t option with desired start time.
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
                var randomRed = Math.random() * 128;
                var randomGreen = Math.random() * 128;
                var randomBlue = Math.random() * 128;
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
