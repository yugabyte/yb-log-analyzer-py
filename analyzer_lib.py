htmlHeader = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
	<meta charset="utf-8">
	<title>Log Analysis Results</title>
    <script type="text/javascript">
    window.onload = function() {
		var toc = document.getElementById("toc");
			var headings = document.getElementsByTagName("h2");
			for (var i = 0; i < headings.length; i++) {
				var heading = headings[i];
				var anchor = document.createElement("a");
				anchor.href = "#" + heading.id;
				anchor.innerHTML = heading.innerHTML;
				var li = document.createElement("li");
				li.appendChild(anchor);
				toc.appendChild(li); 
			}
      var rows = document.querySelectorAll("#main-table tbody tr");
      for (var i = 0; i < rows.length; i++) {
        rows[i].onclick = function() {
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
			setTimeout(function() {
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
			font-family: Arial, sans-serif;
			background-color: #f0f0f0;
            margin-left: 20px;
            line-height: 1.5;
		}
		h2, h3 {
			margin-top: 30px;
			margin-bottom: 15px;
            margin-left: 20px;
			color: #2d3c4d;
		}
		table {
			border-collapse: collapse;
			margin-top: 10px;
			margin-bottom: 30px;
			background-color: white;
			box-shadow: 0 5px 20px rgba(0,0,0,0.3);
			margin-left: 25px;
			margin-right: 25px;
			border-radius: 10px;
			overflow:hidden;
		}
		th, td {
			padding: 10px;
			text-align: left;
			border-bottom: 1px solid #ddd;
			font-size: 15px;
			color: #2d3c4d;
		}
		th {
			background-color: #f2f2f2;
			font-weight: bold;
			cursor: pointer;
		}
		tr:hover {
			background-color: #f5f5f5;
            cursor: pointer;
		}
		a {
			color: #0e7cd4;
			text-decoration: none;
		}
		a:hover {
			text-decoration: underline;
		}
        li {
			text-align: left;
		}
        p {
			margin-left: 20px;
		}
        #toc {
            position:relative;
            top: 0;
            width: auto;
            height: 100%;
            overflow: auto;
            background-color: #f0f0f0;
            margin-left: 25px;
          }
	</style>
</head>"""   # Thanks bing for beautifying the HTML report https://tinyurl.com/2l3hskkl :)

toc = """<div id="toc">
	<h3>Table of Contents</h3>
</div>"""