$(function () {
    $('#container').highcharts({
        chart: {
            type: 'spline',
            zoomType: 'x'
        },
        title: {
            text: '访问量'
        },
        subtitle: {
            text: ''
        },
        xAxis: {
            type: 'datetime',
            labels: {
                overflow: 'justify'
            }
        },
        yAxis: {
            title: {
                text: '(次)'
            },
            min: 0,
            minorGridLineWidth: 0,
            gridLineWidth: 0,
            alternateGridColor: null,
        },
        tooltip: {
            valueSuffix: ' 次'
        },
        plotOptions: {
            spline: {
                lineWidth: 2,
                states: {
                    hover: {
                        lineWidth: 3
                    }
                },
                marker: {
                    enabled: false
                },
                //pointInterval: 3600000, // one hour
                //pointStart: Date.UTC(2015, 4, 31, 0, 0, 0)
            }
        },
        series: ${series | n},
        navigation: {
            menuItemStyle: {
                fontSize: '10px'
            }
        }
    });
});