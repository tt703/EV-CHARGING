package com.standardbank.ev;

import java.net.InetSocketAddress;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import org.java_websocket.WebSocket;
import org.java_websocket.handshake.ClientHandshake;
import org.java_websocket.server.WebSocketServer;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class OCPPServer extends WebSocketServer {

    // DB CONFIG
    private static final String DB_URL = "jdbc:postgresql://localhost:5432/postgres";
    private static final String DB_USER = "postgres";
    private static final String DB_PASS = "Tlotlo";

    // Track Connected Chargers
    private final Map<String, WebSocket> connectedChargers = new ConcurrentHashMap<>();
    
    //shared DB connection
    private Connection dbConnection;

    public OCPPServer(int port) {
        super(new InetSocketAddress(port));
    }

    public static void main(String[] args){
        OCPPServer server = new OCPPServer(8887);
        server.start();
        System.out.println("Java OCPP Server Started on Port 8887");
    }
    @Override
    public void onStart() {
        //Connects to DB once when server starts
        connectToDatabase();
        //This watches DB every 5 seconds for updates
        ScheduledExecutorService executor = Executors.newSingleThreadScheduledExecutor();
        executor.scheduleAtFixedRate(this::syncDatabaseState, 5, 5, TimeUnit.SECONDS);
    }
    //the connection to the database
    private void connectToDatabase(){
        try {
            if (dbConnection != null && !dbConnection.isClosed()) return;
            dbConnection = DriverManager.getConnection(DB_URL, DB_USER, DB_PASS);
            System.out.println("Database Connected Successfully!");
        } catch (Exception e) {
            System.err.println("Critical DB Error: " + e.getMessage());
        }
    }
    private void syncDatabaseState() {
        //ensure DB is alive
        connectToDatabase();
        // Loop through all connected chargers
        for (String chargerId : connectedChargers.keySet()) {
            WebSocket conn = connectedChargers.get(chargerId);
            if (conn != null && conn.isOpen()) {
                String dbStatus = getChargerStatus(chargerId);
                
                // If DB says CHARGING, tell Charger to START
                if ("CHARGING".equals(dbStatus)) {
                    sendRemoteCommand(conn, "RemoteStartTransaction");
                } 
                // If DB says AVAILABLE, tell Charger to STOP
                else if ("AVAILABLE".equals(dbStatus)) {
                    sendRemoteCommand(conn, "RemoteStopTransaction");
                }
            }
        }
    }
    //Websocket handlers
    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        String path = handshake.getResourceDescriptor();
        String chargerId = path.substring(path.lastIndexOf("/") + 1);
        conn.setAttachment(chargerId);
        connectedChargers.put(chargerId, conn);
        System.out.println(" Connected: " + chargerId);
    }

    @Override
    public void onMessage(WebSocket conn, String message) {
        String chargerId = conn.getAttachment();
        try {
            JsonArray json = JsonParser.parseString(message).getAsJsonArray();
            int msgType = json.get(0).getAsInt();
            String msgId = json.get(1).getAsString();
            

            if (msgType == 2) { // Requests
                String action = json.get(2).getAsString();
                JsonObject payload = json.get(3).getAsJsonObject();

                if (action.equals("BootNotification")) {
                    handleBootNotification(conn, msgId, chargerId);
                } else if (action.equals("MeterValues")) {
                    handleMeterValues(conn, msgId, chargerId, payload);
                } else if (action.equals("Heartbeat")) {
                    sendJson(conn, 3, msgId, new JsonObject());
                }
            }
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
    @Override public void onClose(WebSocket c, int i, String s, boolean b) { 
        String id = c.getAttachment();
        if(id!=null) {
            connectedChargers.remove(id);
            // Update DB to OFFLINE when disconnected
            updateChargerStatus(id, "OFFLINE"); 
            System.out.println("Disconnected: " + id);
        }
    }
    
    //logic
    private void handleBootNotification(WebSocket conn, String msgId, String chargerId) {
        System.out.println("Boot: " + chargerId);
        
        // 1. Send OCPP Response
        JsonObject response = new JsonObject();
        response.addProperty("status", "Accepted");
        response.addProperty("currentTime", Instant.now().toString());
        response.addProperty("interval", 300);
        sendJson(conn, 3, msgId, response);
        updateChargerStatus(chargerId, "AVAILABLE");
    }

    private void handleMeterValues(WebSocket conn, String msgId, String chargerId, JsonObject payload) {
        try {
            JsonArray meterValues = payload.getAsJsonArray("meterValue");
            String val = meterValues.get(0).getAsJsonObject()
                         .getAsJsonArray("sampledValue").get(0).getAsJsonObject()
                         .get("value").getAsString();
            double kwh = Double.parseDouble(val);
            
            System.out.println(chargerId + ": +" + kwh + " kWh");
            updateSessionEnergy(chargerId, kwh);
            sendJson(conn, 3, msgId, new JsonObject());
            
        } catch (Exception e) {
            System.err.println("Meter Error: " + e.getMessage());
        }
    }

    private void sendRemoteCommand(WebSocket conn, String command) {
        JsonArray cmd = new JsonArray();
        cmd.add(2);
        cmd.add("cmd_" + System.currentTimeMillis());
        cmd.add(command);
        cmd.add(new JsonObject());
        conn.send(cmd.toString());
    }
    private void sendJson(WebSocket conn, int type, String id, JsonObject payload) {
        JsonArray response = new JsonArray();
        response.add(type); response.add(id); response.add(payload);
        conn.send(response.toString());
    }


    //DB HELPERS
    private void updateChargerStatus(String chargerId, String status) {
        try  {
            if (dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("UPDATE charger SET status = ? WHERE charger_id = ?");
            stmt.setString(1, status);
            stmt.setString(2, chargerId);
            stmt.executeUpdate();
            System.out.println("DB Updated: " + chargerId + " -> " + status);
        } catch (Exception e) {
            System.err.println("DB Error: " + e.getMessage());
        }
    }

    private String getChargerStatus(String chargerId) {
        try  {
            if (dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("SELECT status FROM charger WHERE charger_id = ?");
            stmt.setString(1, chargerId);
            ResultSet rs = stmt.executeQuery();
            if (rs.next()) return rs.getString("status");
        } catch (Exception e) {}
        return "UNKNOWN";
    }

    private void updateSessionEnergy(String chargerId, double kwhAdded) {
        try {
            if(dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("UPDATE charging_sessions SET kwh_delivered = kwh_delivered + ? WHERE charger_id = ? AND status = 'ACTIVE'");
            stmt.setDouble(1, kwhAdded);
            stmt.setString(2, chargerId);
            stmt.executeUpdate();
        } catch (Exception e) {
             System.err.println("DB Error: " + e.getMessage());
        }
    }

    
    @Override public void onError(WebSocket c, Exception e) {}
}