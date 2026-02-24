# 1. Build Stage: Use Maven to compile the code
FROM maven:3.9.4-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

# 2. Run Stage: Use a tiny Java runtime to run the jar
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/ocpp-server-1.0-SNAPSHOT.jar app.jar
EXPOSE 8887
CMD ["java", "-jar", "app.jar"]