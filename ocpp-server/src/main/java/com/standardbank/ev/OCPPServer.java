package com.standardbank.ev;

import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.time.Duration;
import java.time.ZonedDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import com.sun.net.httpserver.HttpServer;

import eu.chargetime.ocpp.JSONServer;
import eu.chargetime.ocpp.ServerEvents;
import eu.chargetime.ocpp.feature.profile.ServerCoreEventHandler;
import eu.chargetime.ocpp.feature.profile.ServerCoreProfile;
import eu.chargetime.ocpp.model.SessionInformation;
import eu.chargetime.ocpp.model.core.AuthorizationStatus;
import eu.chargetime.ocpp.model.core.AuthorizeConfirmation;
import eu.chargetime.ocpp.model.core.AuthorizeRequest;
import eu.chargetime.ocpp.model.core.BootNotificationConfirmation;
import eu.chargetime.ocpp.model.core.BootNotificationRequest;
import eu.chargetime.ocpp.model.core.DataTransferConfirmation;
import eu.chargetime.ocpp.model.core.DataTransferRequest;
import eu.chargetime.ocpp.model.core.DataTransferStatus;
import eu.chargetime.ocpp.model.core.HeartbeatConfirmation;
import eu.chargetime.ocpp.model.core.HeartbeatRequest;
import eu.chargetime.ocpp.model.core.IdTagInfo;
import eu.chargetime.ocpp.model.core.MeterValuesConfirmation;
import eu.chargetime.ocpp.model.core.MeterValuesRequest;
import eu.chargetime.ocpp.model.core.RegistrationStatus;
import eu.chargetime.ocpp.model.core.StartTransactionConfirmation;
import eu.chargetime.ocpp.model.core.StartTransactionRequest;
import eu.chargetime.ocpp.model.core.StatusNotificationConfirmation;
import eu.chargetime.ocpp.model.core.StatusNotificationRequest;
import eu.chargetime.ocpp.model.core.StopTransactionConfirmation;
import eu.chargetime.ocpp.model.core.StopTransactionRequest;

public class OCPPServer {

    // DB CONFIG (Docker Ready)
    private static final String DB_URL = System.getenv("DB_URL") != null ? System.getenv("DB_URL") : "jdbc:postgresql://db:5432/ev_charging";
    private static final String DB_USER = System.getenv("DB_USER") != null ? System.getenv("DB_USER") : "postgres";
    private static final String DB_PASS = System.getenv("DB_PASS") != null ? System.getenv("DB_PASS") : "Tlotlo";

    private Connection dbConnection;
    private JSONServer server;
    private int port;
    
    private final Map<UUID, String> sessionMap = new ConcurrentHashMap<>();

    public OCPPServer(int port) {
        this.port = port;
        connectToDatabase();
        
        ServerCoreProfile coreProfile = new ServerCoreProfile(new ServerCoreEventHandler() {
            
            @Override
            public AuthorizeConfirmation handleAuthorizeRequest(UUID sessionIndex, AuthorizeRequest request) {
                System.out.println("Auth Request from tag: " + request.getIdTag());
                IdTagInfo tagInfo = new IdTagInfo(AuthorizationStatus.Accepted);
                return new AuthorizeConfirmation(tagInfo);
            }

            @Override
            public BootNotificationConfirmation handleBootNotificationRequest(UUID sessionIndex, BootNotificationRequest request) {
                String chargerId = sessionMap.get(sessionIndex);
                System.out.println("BootNotification from: " + chargerId + " (Model: " + request.getChargePointModel() + ")");

                if(!isChargerResgistered(chargerId)){
                    System.err.println("REJECTED: Unregistred charger attempted to connect: " + chargerId);
                    return new BootNotificationConfirmation(ZonedDateTime.now(), 300, RegistrationStatus.Accepted); 
                }
                
                updateChargerStatus(chargerId, "AVAILABLE");

                return new BootNotificationConfirmation(ZonedDateTime.now(), 300, RegistrationStatus.Accepted);
            }

            @Override
            public DataTransferConfirmation handleDataTransferRequest(UUID sessionIndex, DataTransferRequest request) {
                return new DataTransferConfirmation(DataTransferStatus.Accepted);
            }

            @Override
            public HeartbeatConfirmation handleHeartbeatRequest(UUID sessionIndex, HeartbeatRequest request) {
                return new HeartbeatConfirmation(ZonedDateTime.now());
            }

            @Override
            public MeterValuesConfirmation handleMeterValuesRequest(UUID sessionIndex, MeterValuesRequest request) {
                String chargerId = sessionMap.get(sessionIndex);
                
                try {
                    String val = request.getMeterValue()[0].getSampledValue()[0].getValue();
                    double kwh = Double.parseDouble(val);
                    
                    System.out.println(chargerId + " Meter: " + kwh + " kWh");
                    updateSessionEnergy(chargerId, kwh);
                } catch (Exception e) {
                    System.err.println("Malformed MeterValue received");
                }
                
                return new MeterValuesConfirmation();
            }

            @Override
            public StartTransactionConfirmation handleStartTransactionRequest(UUID sessionIndex, StartTransactionRequest request) {
                String chargerId = sessionMap.get(sessionIndex);
                System.out.println("Transaction Started for: " + chargerId);
                
                updateChargerStatus(chargerId, "CHARGING");
                
                int transactionId = (int) (System.currentTimeMillis() % 100000);
                IdTagInfo tagInfo = new IdTagInfo(AuthorizationStatus.Accepted);
                
                return new StartTransactionConfirmation(tagInfo, transactionId);
            }

            @Override
            public StopTransactionConfirmation handleStopTransactionRequest(UUID sessionIndex, StopTransactionRequest request) {
                String chargerId = sessionMap.get(sessionIndex);
                System.out.println("Transaction Stopped for: " + chargerId);
                
                updateChargerStatus(chargerId, "AVAILABLE");
                closeDatabaseSession(chargerId);
                
                notifyPythonBot(chargerId);
                
                IdTagInfo tagInfo = new IdTagInfo(AuthorizationStatus.Accepted);
                StopTransactionConfirmation confirmation = new StopTransactionConfirmation();
                confirmation.setIdTagInfo(tagInfo);
                return confirmation;
            }

            @Override
            public StatusNotificationConfirmation handleStatusNotificationRequest(UUID sessionIndex, StatusNotificationRequest request) {
                System.out.println("Status Update: " + request.getStatus());
                return new StatusNotificationConfirmation();
            }
            
        });

        server = new JSONServer(coreProfile);
    }


    
    public void start() {
        server.open("0.0.0.0", this.port, new ServerEvents() {
            @Override
            public void newSession(UUID sessionIndex, SessionInformation information) {
                String identifier = information.getIdentifier();
                if (identifier.contains("/")){
                    identifier = identifier.substring(identifier.lastIndexOf("/") + 1);
                }
                sessionMap.put(sessionIndex, identifier);
                System.out.println("New Physical Connection: " + identifier);
            }

            @Override
            public void lostSession(UUID sessionIndex) {
                String chargerId = sessionMap.get(sessionIndex);
                System.out.println("Connection Lost: " + chargerId);
                updateChargerStatus(chargerId, "OFFLINE");
                sessionMap.remove(sessionIndex);
            }

            @Override
            public void authenticateSession(SessionInformation information, String username, byte[] password) {
            }
        });
        startInternalApi();
        System.out.println("Secure Java OCPP Server Started on Port " + this.port);
    }

    public int getPort() {
        return this.port;
    }

    private void connectToDatabase() {
        try {
            if (dbConnection != null && !dbConnection.isClosed()) return;
            dbConnection = DriverManager.getConnection(DB_URL, DB_USER, DB_PASS);
            System.out.println("Database Connected Successfully!");
        } catch (Exception e) {
            System.err.println("Critical DB Error: " + e.getMessage());
        }
    }
    private boolean isChargerResgistered(String chargerId){
        try {
            if(dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("SELECT 1 FROM charger WHERE charger_id=?");
            stmt.setString(1, chargerId);
            return stmt.executeQuery().next();
        } catch (Exception e){
            System.err.println("DB AUth Check Error: " + e.getMessage());
            return false;
        }
    }

    private void updateChargerStatus(String chargerId, String status) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("UPDATE charger SET status = ? WHERE charger_id = ?");
            stmt.setString(1, status);
            stmt.setString(2, chargerId);
            stmt.executeUpdate();
        } catch (Exception e) {
            System.err.println("DB Status Update Error: " + e.getMessage());
        }
    }

    private void updateSessionEnergy(String chargerId, double kwhAdded) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("UPDATE charging_sessions SET kwh_delivered = kwh_delivered + ? WHERE charger_id = ? AND status = 'ACTIVE'");
            stmt.setDouble(1, kwhAdded);
            stmt.setString(2, chargerId);
            stmt.executeUpdate();
        } catch (Exception e) {
            System.err.println("DB Energy Update Error: " + e.getMessage());
        }
    }

    private void closeDatabaseSession(String chargerId) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) connectToDatabase();
            PreparedStatement stmt = dbConnection.prepareStatement("UPDATE charging_sessions SET status = 'COMPLETED', end_time = NOW() WHERE charger_id = ? AND status = 'ACTIVE'");
            stmt.setString(1, chargerId);
            stmt.executeUpdate();
        } catch (Exception e) {
            System.err.println("DB Session Close Error: " + e.getMessage());
        }
    }
    private void notifyPythonBot(String chargerId){
        try {
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://backend-api:8000/api/internal/notify-stop/" + chargerId))
                .timeout(Duration.ofSeconds(5))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();
            
            client.sendAsync(request, HttpResponse.BodyHandlers.discarding());
            System.out.println("Webhook fired to python Bot for: " + chargerId);
        } catch (Exception e) {
            System.err.println("Failed to notify Python bot: " + e.getMessage());
        }
    }
    private UUID getSessionIndex(String chargerId){
        for(Map.Entry<UUID, String> entry : sessionMap.entrySet()){
            if (entry.getValue().equals(chargerId)){
                return entry.getKey();
            }
        }
        return null;
    }

    // The new Internal API for Python to talk to
    private void startInternalApi() {
        try {
            HttpServer api = HttpServer.create(new InetSocketAddress(8889), 0);
            api.createContext("/api/command", exchange -> {
                String query = exchange.getRequestURI().getQuery();
                if (query != null) {
                    String chargerId = query.split("&")[0].split("=")[1];
                    String action = query.split("&")[1].split("=")[1];

                    UUID session = getSessionIndex(chargerId);
                    if (session != null) {
                        try {
                            if (action.equals("start")) {
                                server.send(session, new eu.chargetime.ocpp.model.core.RemoteStartTransactionRequest("whatsapp"));
                            } else if (action.equals("stop")) {
                                server.send(session, new eu.chargetime.ocpp.model.core.RemoteStopTransactionRequest(0));
                            }
                        } catch (eu.chargetime.ocpp.OccurenceConstraintException | eu.chargetime.ocpp.UnsupportedFeatureException | eu.chargetime.ocpp.NotConnectedException e) {
                            System.err.println("Failed to send WebSocket command to charger: " + e.getMessage());
                        } catch (Exception e) {
                            System.err.println("Unexpected error: " + e.getMessage());
                        }
                        
                    } else {
                        System.err.println("Cannot send command: Charger " + chargerId + " is not connected.");
                    }
                }
                exchange.sendResponseHeaders(200, -1);
                exchange.close();
            });
            api.setExecutor(null);
            api.start();
            System.out.println("Internal Java API Listening on Port 8889");
        } catch (Exception e) {
            e.printStackTrace();
        }
    
    }
}