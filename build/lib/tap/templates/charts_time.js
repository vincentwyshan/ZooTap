$(function () {
    $('#container').highcharts({
        chart: {
            type: 'spline',
            zoomType: 'x'
        },
        title: {
            text: '响应时间'
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
                text: 'Time (s)'
            },
            min: 0,
            minorGridLineWidth: 0,
            gridLineWidth: 0,
            alternateGridColor: null,
            plotBands: [{ // normal response time
                from: 0,
                to: 500,
                color: 'rgba(0, 0, 0, 0)',
                label: {
                    text: '',
                    style: {
                        color: '#606060'
                    }
                }
            }, { // slow response time
                from: 500,
                to: 5000,
                color: '',
                label: {
                    text: '',
                    style: {
                        color: '#606060'
                    }
                }
            }, ]
        },
        tooltip: {
            valueSuffix: ' s'
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