var hLineConfig = {
    chart: {
        type: 'line',
        height: 220,
    },
    credits: {
        enabled: false
    },
    colors: ['#F68C1F', '#1270b8', '#a6ddf6', '#35ace1', '#4285f4', '#ffd200'],
    title: {
        text: ''
    },
    subtitle: {
        text: ''
    },
    xAxis: {
        type: '',
        categories: [],
//        labels: {
//            style: {"color": '#777', 'font-size': '10px'},
//        },
//        title: {
//            text: ''
//        },
        tickLength: 0,
    },
    yAxis: {
        title: {
            text: '(%)'
        },
        // min: 0,
//        minorGridLineWidth: 0,
//        gridLineWidth: 0,
//        alternateGridColor: null,
//        labels: {
//            format: '{value}',
//            align: 'left',
//            x: 0,
//            y: -2,
//            style: {"color": '#777', 'font-size': '10px'},
//        },
        // opposite: true,
    },
    legend: {
//        itemStyle: {
//            'font-size': '10px'
//        },
//        symbolHeight: 10,
    },
//    tooltip: {
//        pointFormat: '{series.name}：<b>{point.y:,.2f}</b></br>',
//        shared: true,
//    },
    tooltip: {
        shared: true,
        crosshairs: true
    },
    plotOptions: {
        line: {
            lineWidth: 1,
            states: {
                hover: {
                    // lineWidth: 5
                }
            },
            marker: {
                enabled: false
            },
            // pointInterval: 3600000, // one hour
            // pointStart: Date.UTC(2009, 9, 6, 0, 0, 0)
        }
    },
    series: [
    // {
    //     name: '',
    //     data: [
    //         // 3.0
    //     ]
    // },
    ],
    // navigation: {
    //     menuItemStyle: {
    //         fontSize: '10px'
    //     }
    // }
};


$(document).ready(function(){
    hLineConfig.xAxis.categories = ['2010', '2011', '2012', '2013', '2014', '2015', '2016'];
    hLineConfig.series.push({
        name: 'CPU使用率(%)',
        data: [5, 3, 2, 8, 9, 7, 7.1]
    });
    $('.host-load-average>div').highcharts(hLineConfig);
})