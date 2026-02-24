package com.standardbank.ev;

public class App {
    public static void main(String[] args) {
        // Start the server on port 8887
        int port = 8887;
        OCPPServer server = new OCPPServer(port);
        server.start();
        System.out.println("Server is running on port: " + server.getPort());

        //Keep the server running
        try {
            while(true){
                Thread.sleep(1000);
            }
        } catch (InterruptedException e){
            e.printStackTrace();
        }

    }
}