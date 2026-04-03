# Java Spring Boot CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~85 lines of content (~600 tokens)
  - Optimized for Spring Boot 3+ with Maven or Gradle
  - Covers: build/test commands, project layout, patterns, conventions
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Java {17/21}, Spring Boot {3.x}, {Maven / Gradle}, {PostgreSQL / MySQL / H2}
Build: {Maven (mvnw) / Gradle (gradlew)}

## Commands

```bash
# Development
./mvnw spring-boot:run                   # Run the application
# OR: ./gradlew bootRun

# Building
./mvnw clean package                     # Build JAR
./mvnw clean package -DskipTests         # Build without tests
# OR: ./gradlew clean build

# Testing
./mvnw test                              # Run all tests
./mvnw test -Dtest=UserServiceTest       # Single test class
./mvnw test -Dtest="UserServiceTest#testCreateUser"  # Single method
# OR: ./gradlew test --tests UserServiceTest

# Code Quality
./mvnw checkstyle:check                  # Checkstyle (if configured)
./mvnw spotbugs:check                    # SpotBugs (if configured)
```

## Project Structure

```
src/main/java/com/{org}/{project}/
├── {Project}Application.java        # Main class (@SpringBootApplication)
├── config/                          # @Configuration classes
├── controller/                      # @RestController classes (HTTP layer)
├── service/                         # @Service classes (business logic)
├── repository/                      # @Repository interfaces (Spring Data JPA)
├── model/
│   ├── entity/                      # @Entity classes (JPA entities)
│   └── dto/                         # Request/response DTOs (records)
├── exception/                       # Custom exceptions + @ControllerAdvice
└── util/                            # Static helpers
src/main/resources/
├── application.yml                  # Main config (profiles: dev, prod)
└── db/migration/                    # Flyway / Liquibase migrations
src/test/java/                       # Test classes mirror main structure
```

## Patterns

- Constructor injection (no `@Autowired` on fields) -- use `@RequiredArgsConstructor` (Lombok) or explicit constructors
- DTOs as Java records: `public record UserResponse(Long id, String name, String email) {}`
- Service layer owns business logic -- controllers are thin HTTP adapters
- Repository layer: extend `JpaRepository<Entity, ID>`, use `@Query` for custom queries
- Global exception handling via `@RestControllerAdvice`

```java
// Standard controller pattern
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @PostMapping
    public ResponseEntity<UserResponse> create(@Valid @RequestBody UserCreateRequest req) {
        UserResponse user = userService.create(req);
        return ResponseEntity.status(HttpStatus.CREATED).body(user);
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getById(@PathVariable Long id) {
        return ResponseEntity.ok(userService.getById(id));
    }
}
```

## Testing with JUnit 5

- `@SpringBootTest` for integration tests (loads full context)
- `@WebMvcTest(Controller.class)` for controller tests (mock service layer)
- `@DataJpaTest` for repository tests (in-memory DB)
- Use `@MockBean` to mock dependencies in Spring tests
- Assertions: AssertJ (`assertThat`) preferred over JUnit `assertEquals`
- Test naming: `methodName_scenario_expectedResult` (e.g., `create_validInput_returnsCreated`)

## Code Rules

- Java records for DTOs -- not POJOs with getters/setters
- `final` on injected fields and local variables where possible
- No `null` returns from service methods -- use `Optional` or throw exceptions
- Logging via SLF4J (`private static final Logger log = LoggerFactory.getLogger(...)`) -- no `System.out.println`
- Validate request DTOs with `@Valid` and Bean Validation annotations (`@NotBlank`, `@Email`, etc.)

## Do Not

- Do not use field injection (`@Autowired` on fields) -- use constructor injection
- Do not put business logic in controllers or repositories -- use services
- Do not return JPA entities from controllers -- map to DTOs
- Do not manually edit Flyway/Liquibase migration files after they have been applied
- Do not add dependencies without asking first -- check if Spring Boot starters cover the need

<!-- END OF TEMPLATE
  Content: ~85 lines (~600 tokens)
  Overhead per 30-turn session: ~18,000 tokens (pre-cache)
  Optimized for: Spring Boot conventions, layered architecture, JUnit 5 patterns -->
