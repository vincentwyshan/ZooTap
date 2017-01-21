# coding=utf8

from optparse import OptionParser

import cherrypy
from pyramid.paster import get_app


def main():
    usage = "usage: %prog production.ini [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-c', '--config', type="string", dest="config",
                      help="specify config file path.")
    (options, args) = parser.parse_args()

    if not options.config:
        parser.error("Need config path.")

    app = get_app(options.config)

    # Mount the application (or *app*)
    cherrypy.tree.graft(app, "/") 

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Configure the server object
    server.socket_host = "0.0.0.0"
    server.socket_port = 8000
    server.thread_pool = 40

    # For SSL Support
    # server.ssl_module            = 'pyopenssl'
    # server.ssl_certificate       = 'ssl/certificate.crt'
    # server.ssl_private_key       = 'ssl/private.key'
    # server.ssl_certificate_chain = 'ssl/bundle.crt'

    # Subscribe this server
    server.subscribe()

    # Example for a 2nd server (same steps as above):
    # Remember to use a different port

    # server2             = cherrypy._cpserver.Server()

    # server2.socket_host = "0.0.0.0"
    # server2.socket_port = 8080
    # server2.thread_pool = 30
    # server2.subscribe()

    # Start the server engine (Option 1 *and* 2)

    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == '__main__':
    main()

