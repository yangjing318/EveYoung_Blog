/**
 * Created by yangjing on 2017/5/23.
 */


/**
 * 具体流程:
 * 1.点击按钮提交
 * 2.js脚本的postJson函数把数据传出去
 * 3.@post('api/blogs')的处理函数把数据写进数据库, 然后把生成的blog id用json传回
 * 4.最后postJson的第三个参数的回调函数接收到blog id的值, 再用location.assign函数重定向到新建的日志网址
 *
 */
var vm = new Vue ({
    el: '#blog',
    data: {
        message: '',
        blog: {
            message: '',
            summary: '',
            content: ''
        }
    },
    computed: {
        method: function() {
            return location.pathname.slice(-5) === '/edit' ? 'PUT' : 'POST';
        },
        url: function () {
            return '/api/blog/' + ((this.method === 'PUT') ? getUrlParams('id') : '');
        }
    },
    ready: function () {
        if (this.method === 'PUT') {
            $.ajax({
                url: this.url,
                success: function(blog) {
                    vm.blog = blog;
                }
            })
        }
    },
    methods: {
        submit: function () {
            $.ajax({
                url: this.url,
                type: this.method,
                data: this.blog,
                success: function (data) {
                    if (data && data.error) {
                        return showAlert(vm, data.message || data.data || data);
                    }
                    return location.assign(location.pathname.split('manage')[0] + 'blog/' + data.id);
                }
            });
        }
    }
});